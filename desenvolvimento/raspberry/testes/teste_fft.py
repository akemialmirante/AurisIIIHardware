#nesse programa estamos testando a separação grave/medio/agudo sem mexer no sistema principal, apenas analisando por terminal

import subprocess 
import numpy as np

FONTE = "auris_combined.monitor"
AMOSTRAGEM = 48000 
CANAIS = 2
BLOCO = 1024 #olhar isso daqui por conta do delay

#comando parec (captura de audio do sistema)
cmd = [
	"parec",
	"-d",
	FONTE,
	"--raw",
	"--format=float32le",
	"--latency-msec=45",
	f"--rate={AMOSTRAGEM}",
	f"--channels={CANAIS}"
	]

processo = subprocess.Popen(cmd, stdout=subprocess.PIPE)
print("Teste FFT iniciado. Aguardando áudio.")
print("Ctrl+C para sair")

def energia_banda(freqs, espectro, f_min, f_max):
	
	indices = (freqs >= f_min) & (freqs < f_max)
	
	#se nao houver frequencia nessa faixa, retorna 0
	if not np.any(indices):
		return 0.0
		
	#calculo media
	return np.mean(espectro[indices])

try:
	while True:
		dados = processo.stdout.read(BLOCO*CANAIS*4)
		if not dados:
			continue
			
		#conversao bytes->float
		audio = np.frombuffer(dados, dtype=np.float32)
		if audio.size == 0:
			continue 
			
		audio = audio.reshape(-1, CANAIS)
		
		#transforma em mono (E+D = media)
		mono = (audio[:,0] + audio[:,1]) /2.0
		
		#janela de Hann
		janela = np.hanning(len(mono))
		
		#redução de artefatos no espectro de frequencia
		sinal = mono * janela
		
		fft = np.fft.rfft(sinal)
		
		#pega o modulo da transformada (representa intensidade de cada freq)
		espectro = np.abs(fft)
		
		#vertor de frequencias
		freqs = np.fft.rfftfreq(len(sinal), 1/AMOSTRAGEM)
		
		grave = energia_banda(freqs, espectro, 20, 250) #considera grave de 20 a 250hz
		
		medio = energia_banda(freqs, espectro, 250, 2000) #considera media de 250 a 2000hz
		
		agudo = energia_banda(freqs, espectro, 2000, 8000) #considera agudo de 2000 a 8000hz 
		
		total = grave + medio + agudo
		
		if total >0:
			#normalizamos
			grave_n = grave/total
			medio_n = medio/total
			agudo_n = agudo/total
			
		else:
			grave_n = 0
			medio_n = 0
			agudo_n = 0
		
		#conversao pra a proporção do nosso pwm
		
		grave_pwm = int(max(0, min(255, grave_n*255)))
		medio_pwm = int(max(0, min(255, medio_n*255)))
		agudo_pwm = int(max(0, min(255, agudo_n*255)))
		
		
		print(
			f"grave={grave_pwm:3d} "
			f"medio={medio_pwm:3d} "
			f"agudo={agudo_pwm:3d} "
		)
		
except KeyboardInterrupt:
	print("Encerrando programa...")
	processo.terminate()
			
		
