#Esse código faz com que o motor seja sensível diretamente a entrada do microfone, nada mais...

import sounddevice as sd
import numpy as np
import serial
import time

DEVICE_INDEX = 2
SERIAL_PORT = '/dev/ttyACM0'

ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)
time.sleep(2)

ultimo_valor = 0

def callback(indata, frames, time_info, status):
    global ultimo_valor

    if status:
        print(status)

    volume = np.linalg.norm(indata) * 20
    intensidade = int(min(max(volume, 0), 255))
    ultimo_valor = intensidade

with sd.InputStream(
    device=DEVICE_INDEX,
    channels=1,
    samplerate=44100,
    blocksize=1024,
    callback=callback
):
    print("Rodando... Ctrl+C para parar.")
    while True:
        ser.write(f"{ultimo_valor}\n".encode())
        time.sleep(0.03)