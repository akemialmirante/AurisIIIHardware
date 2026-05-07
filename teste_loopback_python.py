import sounddevice as sd
import numpy as np
import serial
import time

PORTA = '/dev/ttyACM0'
BAUD = 115200

BLOCO = 1024
GANHO = 8.0
NOISE_GATE = 0.015
SUAVIZACAO = 0.2
VALOR_MAXIMO = 255

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
    print("2 - Áudio interno/loopback")
    modo = input("Digite 1 ou 2: ").strip()
    return modo


def escolher_dispositivo(modo):
    if modo == "1":
        dispositivo = encontrar_dispositivo_por_nome("USB PnP", entrada=True)
        return dispositivo, 1

    elif modo == "2":
        dispositivo = encontrar_dispositivo_por_nome("Loopback", entrada=True)
        return dispositivo, None

    else:
        raise ValueError("Modo inválido")


def obter_config_audio(dispositivo, canais_desejados=None):
    info = sd.query_devices(dispositivo)

    canais_maximos = int(info["max_input_channels"])
    amostragem = int(info["default_samplerate"])

    if canais_maximos <= 0:
        raise ValueError("Esse dispositivo não possui canais de entrada.")

    if canais_desejados is None:
        canais = min(2, canais_maximos)
    else:
        canais = min(canais_desejados, canais_maximos)

    return canais, amostragem


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

    if nivel > 1.0:
        nivel = 1.0

    if nivel < 0.0:
        nivel = 0.0

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


def processar_bloco(indata, canais):
    if canais == 1:
        audio = indata[:, 0].astype(np.float32)

    else:
        audio_esq = indata[:, 0].astype(np.float32)
        audio_dir = indata[:, 1].astype(np.float32)
        audio = (audio_esq + audio_dir) / 2.0

    rms = calcular_rms(audio)
    rms = aplicar_noise_gate(rms)
    nivel = aplicar_ganho(rms)
    nivel_suave = suavizar_nivel(nivel)
    pwm = converter_para_pwm(nivel_suave)

    enviar_pwm(pwm)

    print(f"rms={rms:.4f} nivel={nivel:.4f} suave={nivel_suave:.4f} pwm={pwm}")


def criar_callback(canais):
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status)

        try:
            processar_bloco(indata, canais)
        except Exception as e:
            print("Erro no processamento:", e)

    return audio_callback


def main():
    global ser, modo_atual

    listar_dispositivos()

    modo_atual = escolher_modo()
    dispositivo, canais_desejados = escolher_dispositivo(modo_atual)

    canais, amostragem = obter_config_audio(dispositivo, canais_desejados)

    ser = abrir_serial()

    callback = criar_callback(canais)

    info = sd.query_devices(dispositivo)

    print("\nIniciando captura...")
    print(f"Modo selecionado: {modo_atual}")
    print(f"Dispositivo detectado: {dispositivo} - {info['name']}")
    print(f"Canais usados: {canais}")
    print(f"Amostragem usada: {amostragem} Hz")

    if modo_atual == "1":
        print("Usando microfone USB.")
    elif modo_atual == "2":
        print("Usando áudio interno/loopback.")

    with sd.InputStream(
        device=dispositivo,
        channels=canais,
        samplerate=amostragem,
        blocksize=BLOCO,
        dtype='float32',
        callback=callback
    ):
        print("Capturando áudio. Ctrl+C para sair.")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nEncerrando...")

    ser.close()


if __name__ == "__main__":
    main()



