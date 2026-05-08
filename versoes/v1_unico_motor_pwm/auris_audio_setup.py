import subprocess
import sys
import time

NOME_COMBINADO = "auris_combined"


def rodar(cmd, capturar=True):
    resultado = subprocess.run(cmd, text=True, capture_output=capturar)

    if resultado.returncode != 0:
        erro = resultado.stderr.strip() if resultado.stderr else ""
        raise RuntimeError(f"Erro ao executar: {' '.join(cmd)}\n{erro}")

    return resultado.stdout if capturar else ""


def comando_existe(nome):
    resultado = subprocess.run(["which", nome], text=True, capture_output=True)
    return resultado.returncode == 0


def garantir_dependencias():
    faltando = []

    for cmd in ["pactl", "wpctl", "parec"]:
        if not comando_existe(cmd):
            faltando.append(cmd)

    if faltando:
        print("Faltam comandos necessários:", ", ".join(faltando))
        print("Instale com:")
        print("sudo apt update")
        print("sudo apt install pulseaudio-utils wireplumber")
        sys.exit(1)


def garantir_loopback():
    sinks = rodar(["pactl", "list", "short", "sinks"])

    if "snd_aloop" in sinks or "loopback" in sinks.lower():
        return

    print("Loopback não encontrado. Tentando carregar snd-aloop...")
    resultado = subprocess.run(["sudo", "modprobe", "snd-aloop"])

    if resultado.returncode != 0:
        raise RuntimeError("Não foi possível carregar snd-aloop.")

    time.sleep(2)


def listar_sinks():
    saida = rodar(["pactl", "list", "short", "sinks"])
    sinks = []

    for linha in saida.splitlines():
        partes = linha.split("\t")
        if len(partes) >= 2:
            sinks.append({
                "id": partes[0],
                "nome": partes[1],
                "linha": linha
            })

    return sinks


def escolher_sink_loopback(sinks):
    for sink in sinks:
        nome = sink["nome"].lower()
        if "snd_aloop" in nome or "loopback" in nome:
            return sink["nome"]

    raise RuntimeError("Não encontrei sink de loopback.")


def escolher_sink_saida_real(sinks):
    candidatos_usb = []

    for sink in sinks:
        nome = sink["nome"].lower()

        if NOME_COMBINADO in nome:
            continue

        if "snd_aloop" in nome or "loopback" in nome:
            continue

        if "usb" in nome or "c-media" in nome or "pcm2902" in nome:
            candidatos_usb.append(sink["nome"])

    if candidatos_usb:
        return candidatos_usb[0]

    for sink in sinks:
        nome = sink["nome"].lower()

        if NOME_COMBINADO in nome:
            continue

        if "snd_aloop" in nome or "loopback" in nome:
            continue

        return sink["nome"]

    raise RuntimeError("Não encontrei saída real de áudio.")


def descarregar_combinado_antigo():
    saida = rodar(["pactl", "list", "short", "modules"])

    for linha in saida.splitlines():
        if "module-combine-sink" in linha and NOME_COMBINADO in linha:
            modulo_id = linha.split("\t")[0]
            print(f"Removendo combinado antigo: módulo {modulo_id}")
            subprocess.run(["pactl", "unload-module", modulo_id])


def criar_combinado(saida_real, loopback):
    print("Criando sink combinado:")
    print("Saída real:", saida_real)
    print("Loopback:", loopback)

    modulo = rodar([
        "pactl",
        "load-module",
        "module-combine-sink",
        f"sinks={saida_real},{loopback}",
        f"sink_name={NOME_COMBINADO}",
        "sink_properties=device.description=Auris_Combined"
    ])

    print("Módulo criado:", modulo.strip())


def definir_padrao():
    rodar(["pactl", "set-default-sink", NOME_COMBINADO])

    entradas = rodar(["pactl", "list", "short", "sink-inputs"])

    for linha in entradas.splitlines():
        partes = linha.split("\t")
        if partes:
            entrada_id = partes[0]
            subprocess.run(["pactl", "move-sink-input", entrada_id, NOME_COMBINADO])


def verificar_monitor():
    fontes = rodar(["pactl", "list", "short", "sources"])

    if f"{NOME_COMBINADO}.monitor" not in fontes:
        raise RuntimeError("O monitor auris_combined.monitor não apareceu.")

    print("Monitor disponível:", f"{NOME_COMBINADO}.monitor")


def main():
    garantir_dependencias()
    garantir_loopback()

    sinks = listar_sinks()

    loopback = escolher_sink_loopback(sinks)
    saida_real = escolher_sink_saida_real(sinks)

    descarregar_combinado_antigo()
    criar_combinado(saida_real, loopback)
    definir_padrao()
    verificar_monitor()

    print("\nConfiguração pronta.")
    print('Fonte do sistema: "auris_combined.monitor"')


if __name__ == "__main__":
    main()



