# path: services/chat_scoring_service.py
from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlmodel import select
from models.chat_score_event import ChatScoreEvent
from models.pipeline_estado import PipelineEstado


# ---------------------------
# Normalización y matching
# ---------------------------

def _norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )
    # deja letras/números/espacios, lo demás a espacio
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _compile_keyword(kw: str) -> re.Pattern:
    """
    - Si es frase (tiene espacios): matchea como substring normalizado
    - Si es una palabra: matchea con bordes para evitar falsos positivos (ej "plan" en "planeando")
    """
    k = _norm_text(kw)
    if not k:
        return re.compile(r"(?!x)x")  # nunca matchea

    if " " in k:
        return re.compile(re.escape(k), re.IGNORECASE)

    # palabra completa (bordes)
    return re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE)


# ---------------------------
# Reglas (expandidas)
# ---------------------------

REGLAS_SCORE = [
    # 💰 PRECIO / PLANES / PAGO
    {
        "palabras": [
            "precio", "cuanto", "cuánto", "vale", "sale", "costo", "coste", "tarifa", "valor",
            "abono", "mensual", "mensualidad", "cuota",
            "planes", "plan", "promo", "promocion", "promoción", "oferta", "descuento",
            "instalacion gratis", "instalación gratis",
            "forma de pago", "pago", "factura",
        ],
        "delta": 2,
        "motivo": "Consulta comercial",
    },

    # 📡 INTERÉS TÉCNICO
    {
        "palabras": [
            "fibra", "fibra optica", "fibra óptica", "ftth",
            "velocidad", "megas", "mb", "gb",
            "subida", "bajada", "simetrico", "simétrico",
            "latencia", "ping",
            "wifi", "router", "onu",
            "ip publica", "ip pública", "publica", "pública",
            "se corta", "cortes", "microcortes", "intermitente",
            "netflix", "streaming", "jugar", "gaming",
        ],
        "delta": 3,
        "motivo": "Interés técnico",
    },

    # 📍 COBERTURA / ZONA / UBICACIÓN
    {
        "palabras": [
            "cobertura", "zona", "barrio", "localidad", "ciudad",
            "llega", "llegan", "llegaria", "llegaría",
            "direccion", "dirección", "domicilio", "calle", "altura",
            "manzana", "lote",
            "ubicacion", "ubicación", "maps", "google maps",
            "disponibilidad", "cupo",
            "instalan en", "instalar en",
        ],
        "delta": 4,
        "motivo": "Consulta de cobertura",
    },

    # 🛠 INSTALACIÓN / LOGÍSTICA
    {
        "palabras": [
            "instalacion", "instalación", "instalar", "instalan",
            "cuando instalan", "cuando pueden", "cuanto tardan", "cuánto tardan",
            "turno", "fecha", "horario",
            "tecnico", "técnico", "visita",
        ],
        "delta": 4,
        "motivo": "Interés en instalación",
    },

    # ✅ INTENCIÓN DE CONTRATACIÓN
    {
        "palabras": [
            "quiero", "me interesa", "lo quiero",
            "quiero contratar", "me interesa contratar",
            "contratar", "alta", "dar de alta", "activar", "activacion", "activación",
            "pasame los datos", "pasame info", "pásame info",
            "confirmo", "dale", "ok", "joya",
        ],
        "delta": 6,
        "motivo": "Intención de contratación",
    },

    # ⏱ URGENCIA
    {
        "palabras": [
            "urgente", "lo antes posible", "ya",
            "hoy", "mañana", "esta semana",
        ],
        "delta": 3,
        "motivo": "Urgencia",
    },

    # 🛰 SATELITAL / RURAL
    {
        "palabras": [
            "satelite", "satélite", "starlink", "star link",
            "rural", "campo", "zona rural",
        ],
        "delta": 3,
        "motivo": "Interés satelital",
    },

    # 🔄 COMPETENCIA
    {
        "palabras": [
            "comparar", "otra empresa",
            "movistar", "personal", "claro", "telecom", "iplan",
            "telecentro", "flow", "directv", "direc tv",
        ],
        "delta": 1,
        "motivo": "Comparación con competencia",
    },

    # ❌ OBJECIONES (ojo: saqué "no" solo porque rompe todo)
    {
        "palabras": [
            "muy caro", "carisimo", "carísimo",
            "no me sirve", "no quiero", "no puedo",
            "por ahora no", "mas adelante", "más adelante",
            "despues veo", "después veo", "luego veo",
            "ya tengo", "ya cuento con",
        ],
        "delta": -4,
        "motivo": "Objeción",
    },

    # 🛑 RECHAZO FUERTE
    {
        "palabras": [
            "no gracias", "cancelar", "baja", "dar de baja",
            "no me interesa", "olvidate", "olvídate",
            "no molesten", "stop","spam","no quiero el servicio", "no me sirve"
        ],
        "delta": -8,
        "motivo": "Rechazo definitivo",
    },
]

# Compilamos patterns una vez
for r in REGLAS_SCORE:
    r["_patterns"] = [_compile_keyword(k) for k in r["palabras"]]


# ---------------------------
# Score
# ---------------------------

def calcular_score_chat(mensajes: list[dict]) -> list[dict]:
    """
    mensajes: lista de dicts con al menos:
      - "mensaje": str
    opcional:
      - "from_me": bool  (si viene, se ignoran los True)
    """
    partes: list[str] = []

    for m in mensajes or []:
        if m.get("from_me") is True:
            continue
        txt = (m.get("mensaje") or "").strip()
        if not txt:
            continue
        partes.append(_norm_text(txt))

    texto_total = " ".join(partes)

    eventos: list[dict[str, Any]] = []
    for regla in REGLAS_SCORE:
        if any(p.search(texto_total) for p in regla["_patterns"]):
            eventos.append(
                {"origen": "rule", "delta": regla["delta"], "motivo": regla["motivo"]}
            )

    return eventos


def aplicar_score(chat, eventos, session):
    score = chat.score_actual or 0

    for ev in eventos:
        score += ev["delta"]
        session.add(
            ChatScoreEvent(
                chat_id=chat.id,
                origen=ev["origen"],
                motivo=ev["motivo"],
                delta=ev["delta"],
            )
        )

    chat.score_actual = score
    chat.pipeline_estado_id = determinar_pipeline(score, session)
    session.add(chat)


def determinar_pipeline(score, session):
    estado = session.exec(
        select(PipelineEstado)
        .where(PipelineEstado.score_min <= score)
        .where(PipelineEstado.score_max >= score)
    ).first()

    return estado.id if estado else None
