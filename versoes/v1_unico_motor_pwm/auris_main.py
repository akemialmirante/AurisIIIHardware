import sounddevice as sd
import numpy as np
import serial
import time
import subprocess

PORTA = '/dev/ttyACM0'
BAUD = 115200

BLOCO = 1024
GANHO = 8.0
NOISE_GATE = 0.015
SUAVIZACAO = 0.2
VALOR_MAXIMO = 255

FONTE_SISTEMA = "auris_combined.monitor"
AMOSTRAGEM_SISTEMA = 48000
CANAIS_SISTEMA = 2

LIMIAR_AGUARDANDO_AUDIO = 0.001
CICLOS_PARA_AVISO = 20

ser = None
suave = 0.0
modo_atual = None


def listar_dispositivos():
    dispositivos = sd.query_devices()
    print("\nDispositivos disponíveis:")
    for i, d in enumerate(dispositivos):
        print(
            f"{i}: {d['name']} | "
            f"in={d['max_input_channels']} | "
            f"out={d['max_output_channels']} | "
            f"sr={d['default_samplerate']}"
        )


def encontrar_dispositivo_por_nome(palavra_chave, entrada=True):
    dispositivos = sd.query_devices()

    for i, d in enumerate(dispositivos):
        nome = d["name"].lower()

        if palavra_chave.lower() in nome:
            if entrada and d["max_input_channels"] > 0:
                return i

            if not entrada and d["max_output_channels"] > 0:
                return i

    raise ValueError(f"Dispositivo com '{palavra_chave}' não encontrado.")


def escolher_modo():
    print("\nEscolha a fonte de áudio:")
    print("1 - Microfone USB")
    print("2 - Áudio interno/navegador")
    modo = input("Digite 1 ou 2: ").strip()
    return modo


def abrir_serial():
    conexao = serial.Serial(PORTA, BAUD)
    time.sleep(2)
    return conexao


def calcular_rms(audio):
    return np.sqrt(np.mean(audio ** 2))


def aplicar_noise_gate(rms):
    if rms < NOISE_GATE:
        return 0.0
    return rms


def aplicar_ganho(rms):
    nivel = rms * GANHO
    nivel = max(0.0, min(1.0, nivel))
    return nivel


def suavizar_nivel(nivel):
    global suave
    suave = SUAVIZACAO * nivel + (1.0 - SUAVIZACAO) * suave
    return suave


def converter_para_pwm(valor):
    pwm = int(valor * VALOR_MAXIMO)
    pwm = max(0, min(255, pwm))
    return pwm


def enviar_pwm(pwm):
    global ser
    ser.write(f"{pwm}\n".encode())


def processar_audio(audio):
    rms = calcular_rms(audio)

    rms_gate = aplicar_noise_gate(rms)
    nivel = aplicar_ganho(rms_gate)
    nivel_suave = suavizar_nivel(nivel)
    pwm = converter_para_pwm(nivel_suave)

    enviar_pwm(pwm)

    print(f"rms={rms_gate:.4f} nivel={nivel:.4f} suave={nivel_suave:.4f} pwm={pwm}")


def iniciar_microfone():
    dispositivo = encontrar_dispositivo_por_nome("USB PnP", entrada=True)
    info = sd.query_devices(dispositivo)

    canais = 1
    amostragem = int(info["default_samplerate"])

    print("\nUsando microfone USB.")
    print(f"Dispositivo: {dispositivo} - {info['name']}")
    print(f"Canais: {canais}")
    print(f"Amostragem: {amostragem} Hz")
    print("Aguardando áudio...")

    sem_audio = 0

    def callback(indata, frames, time_info, status):
        nonlocal sem_audio

        if status:
            print(status)

        audio = indata[:, 0].astype(np.float32)
        rms = calcular_rms(audio)

        if rms < LIMIAR_AGUARDANDO_AUDIO:
            sem_audio += 1

            if sem_audio == CICLOS_PARA_AVISO:
                print("Aguardando áudio...")

            return

        sem_audio = 0
        processar_audio(audio)

    with sd.InputStream(
        device=dispositivo,
        channels=canais,
        samplerate=amostragem,
        blocksize=BLOCO,
        dtype='float32',
        callback=callback
    ):
        print("Capturando microfone. Ctrl+C para sair.")
        while True:
            time.sleep(0.1)


def iniciar_audio_sistema():
    cmd = [
        "parec",
        "-d", FONTE_SISTEMA,
        "--raw",
        "--format=float32le",
        f"--rate={AMOSTRAGEM_SISTEMA}",
        f"--channels={CANAIS_SISTEMA}"
    ]

    processo = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    print("\nUsando áudio interno/navegador.")
    print(f"Fonte: {FONTE_SISTEMA}")
    print(f"Canais: {CANAIS_SISTEMA}")
    print(f"Amostragem: {AMOSTRAGEM_SISTEMA} Hz")
    print("Capturando áudio do sistema. Ctrl+C para sair.")
    print("Aguardando áudio...")

    sem_audio = 0

    try:
        while True:
            dados = processo.stdout.read(BLOCO * CANAIS_SISTEMA * 4)

            if not dados:
                continue

            audio = np.frombuffer(dados, dtype=np.float32)

            if audio.size == 0:
                continue

            audio = audio.reshape(-1, CANAIS_SISTEMA)

            mono = (audio[:, 0] + audio[:, 1]) / 2.0

            rms = calcular_rms(mono)

            if rms < LIMIAR_AGUARDANDO_AUDIO:
                sem_audio += 1

                if sem_audio == CICLOS_PARA_AVISO:
                    print("Aguardando áudio...")

                continue

            sem_audio = 0
            processar_audio(mono)

    except KeyboardInterrupt:
        processo.terminate()
        raise


def main():
    global ser, modo_atual

    listar_dispositivos()

    modo_atual = escolher_modo()

    ser = abrir_serial()

    try:
        if modo_atual == "1":
            iniciar_microfone()

        elif modo_atual == "2":
            iniciar_audio_sistema()

        else:
            raise ValueError("Modo inválido")

    except KeyboardInterrupt:
        print("\nEncerrando...")

    finally:
        if ser is not None:
            ser.close()


if __name__ == "__main__":
    main()



