#Nesse código apenas vemos se o loopback funciona e o python recebe os dados (via impressao no terminal)
import subprocess
import numpy as np

FONTE = "auris_combined.monitor"
AMOSTRAGEM = 48000
CANAIS = 2
BLOCO = 1024

cmd = [
    "parec",
    "-d", FONTE,
    "--raw",
    "--format=float32le",
    f"--rate={AMOSTRAGEM}",
    f"--channels={CANAIS}"
]

processo = subprocess.Popen(cmd, stdout=subprocess.PIPE)

print("Capturando áudio do navegador (loopback)... Ctrl+C para sair.")

try:
    while True:
        dados = processo.stdout.read(BLOCO * CANAIS * 4)

        if not dados:
            continue

        audio = np.frombuffer(dados, dtype=np.float32)

        if audio.size == 0:
            continue

        audio = audio.reshape(-1, CANAIS)

        # mistura estéreo em mono
        mono = (audio[:, 0] + audio[:, 1]) / 2.0

        rms = np.sqrt(np.mean(mono ** 2))
        pico = np.max(np.abs(mono))

        print(f"rms={rms:.6f} pico={pico:.6f}")

except KeyboardInterrupt:
    print("\nEncerrando...")
    processo.terminate()


