import re

def parsear_chat(path):
    mensajes = []

    # Regex tolerante a formatos reales de WhatsApp
    patron = re.compile(
        r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s(\d{1,2}:\d{2})\s-\s([^:]+):\s(.*)$"
    )

    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        lineas = f.readlines()

    mensaje_actual = None

    for linea in lineas:
        linea = linea.strip()

        match = patron.match(linea)

        if match:
            # Guardar mensaje anterior
            if mensaje_actual:
                mensajes.append(mensaje_actual)

            fecha, hora, usuario, texto = match.groups()

            mensaje_actual = {
                "fecha": normalizar_fecha(fecha),
                "hora": hora,
                "usuario": usuario.strip(),
                "mensaje": texto.strip(),
            }
        else:
            # Mensaje multilínea
            if mensaje_actual:
                mensaje_actual["mensaje"] += "\n" + linea

    # Guardar último mensaje
    if mensaje_actual:
        mensajes.append(mensaje_actual)

    return mensajes


def normalizar_fecha(fecha):
    """
    Convierte:
    5/1/26  -> 05/01/2026
    05/01/2026 -> 05/01/2026
    """
    partes = fecha.split("/")
    dia = partes[0].zfill(2)
    mes = partes[1].zfill(2)
    anio = partes[2]

    if len(anio) == 2:
        anio = "20" + anio

    return f"{dia}/{mes}/{anio}"
