import subprocess
import numpy as np

FONTE = "auris_combined.monitor"
AMOSTRAGEM = 48000
CANAIS = 2
BLOCO = 2048

LATENCIA = 45

GANHO_GRAVE = 8.0
GANHO_MEDIO = 35.0
GANHO_AGUDO = 90.0

GATE_GRAVE = 0.00012
GATE_MEDIO = 0.0005
GATE_AGUDO = 0.00012

SUAVIZACAO_GRAVE = 0.25
SUAVIZACAO_MEDIO = 0.20
SUAVIZACAO_AGUDO = 0.15

grave_suave = 0.0
medio_suave = 0.0
agudo_suave = 0.0

cmd = [
    "parec",
    "-d", FONTE,
    "--raw",
    "--format=float32le",
    f"--latency-msec={LATENCIA}",
    f"--rate={AMOSTRAGEM}",
    f"--channels={CANAIS}"
]

processo = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)

janela = np.hanning(BLOCO)
freqs = np.fft.rfftfreq(BLOCO, 1 / AMOSTRAGEM)

idx_grave = (freqs >= 20) & (freqs < 180)
idx_medio = (freqs >= 300) & (freqs < 1800)
idx_agudo = (freqs >= 3000) & (freqs < 7000)

print("Teste FFT com energia real iniciado.")
print("Ctrl+C para sair.")

def energia_banda(espectro, indices):
    if not np.any(indices):
        return 0.0
    return np.mean(espectro[indices]) / BLOCO


def aplicar_gate(valor, gate):
    if valor < gate:
        return 0.0
    return valor


def aplicar_ganho(valor, ganho):
    return max(0.0, min(1.0, valor * ganho))


def suavizar(valor, anterior, fator):
    return fator * valor + (1.0 - fator) * anterior


def para_pwm(valor):
    return int(max(0, min(255, valor * 255)))


contador = 0

try:
    while True:
        dados = processo.stdout.read(BLOCO * CANAIS * 4)

        if not dados:
            continue

        audio = np.frombuffer(dados, dtype=np.float32)

        if audio.size != BLOCO * CANAIS:
            continue

        audio = audio.reshape(-1, CANAIS)

        esquerdo = audio[:, 0]
        direito = audio[:, 1]

        mono = (esquerdo + direito) / 2.0

        sinal = mono * janela

        fft = np.fft.rfft(sinal)
        espectro = np.abs(fft)

        grave = energia_banda(espectro, idx_grave)
        medio = energia_banda(espectro, idx_medio)
        agudo = energia_banda(espectro, idx_agudo)

        grave = aplicar_gate(grave, GATE_GRAVE)
        medio = aplicar_gate(medio, GATE_MEDIO)
        agudo = aplicar_gate(agudo, GATE_AGUDO)

        grave = aplicar_ganho(grave, GANHO_GRAVE)
        medio = aplicar_ganho(medio, GANHO_MEDIO)
        agudo = aplicar_ganho(agudo, GANHO_AGUDO)

        grave_suave = suavizar(grave, grave_suave, SUAVIZACAO_GRAVE)
        medio_suave = suavizar(medio, medio_suave, SUAVIZACAO_MEDIO)
        agudo_suave = suavizar(agudo, agudo_suave, SUAVIZACAO_AGUDO)

        grave_pwm = para_pwm(grave_suave)
        medio_pwm = para_pwm(medio_suave)
        agudo_pwm = para_pwm(agudo_suave)

        contador += 1

        if contador >= 5:
            contador = 0
            print(
                f"grave={grave_pwm:3d} "
                f"medio={medio_pwm:3d} "
                f"agudo={agudo_pwm:3d}"
            )

except KeyboardInterrupt:
    print("\nEncerrando...")
    processo.terminate()

