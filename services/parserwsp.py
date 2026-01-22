
from __future__ import annotations

import os
import re

WHATSAPP_PREFIX = "Chat de WhatsApp con "

# Solo símbolos típicos de teléfono (sin letras)
_PHONE_ONLY_RE = re.compile(r"^\+?[\d\s\-\(\)]+$")


def _strip_extension_and_prefix(filename: str) -> str:
    base = os.path.basename(filename).strip()
    base_no_ext = os.path.splitext(base)[0].strip()
    if base_no_ext.startswith(WHATSAPP_PREFIX):
        base_no_ext = base_no_ext[len(WHATSAPP_PREFIX):].strip()
    return base_no_ext


def _normalize_phone(text: str) -> str:
    text = text.strip()
    keep_plus = text.startswith("+")
    digits = "".join(ch for ch in text if ch.isdigit())
    return f"+{digits}" if keep_plus else digits


def classify_whatsapp_filename(filename: str) -> tuple[str, str | None, int]:
    """
    Returns (nombre, telefono, estado)

    estado:
      - 0 => NO agendado (solo teléfono)
      - 1 => agendado / contacto (contiene letras, aunque arranque con números)
    """
    nombre = _strip_extension_and_prefix(filename)

    if not nombre:
        return "", None, 1

    # Si hay letras => contacto (ej: "149 LUIS JESUS TOSI")
    if any(ch.isalpha() for ch in nombre):
        return nombre, None, 1

    # Si no hay letras, y es formato teléfono => no agendado
    if _PHONE_ONLY_RE.match(nombre):
        normalized = _normalize_phone(nombre)
        if len(normalized.lstrip("+")) >= 7:
            return nombre, normalized, 0

    # fallback conservador: si no hay letras pero tampoco parece teléfono puro, tratá como contacto
    return nombre, None, 1


# --- quick demo ---
if __name__ == "__main__":
    samples = [
        "Chat de WhatsApp con +54 9 261 276-7072.txt",
        "Chat de WhatsApp con +54 9 261 270-8812.zip",
        "Chat de WhatsApp con +54 9 261 276-6367",
        "Chat de WhatsApp con 149 LUIS JESUS TOSI.txt",
        "Chat de WhatsApp con 123clientecalle12.txt",
    ]
    for s in samples:
        nombre, tel, estado = classify_whatsapp_filename(s)
        print(s, "=>", {"nombre": nombre, "telefono": tel, "estado": estado})