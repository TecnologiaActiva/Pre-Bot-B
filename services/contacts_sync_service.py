# services/contacts_sync_service.py

from __future__ import annotations

import re
import unicodedata
import math
from typing import Any

import pandas as pd
from sqlmodel import select

from models.contactos import Contacto
from models.chat import Chat


# -------------------------
# Normalizadores
# -------------------------

def _norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _clean_outlook_name(name: str) -> str:
    """
    Outlook a veces trae "001 JUAN PEREZ".
    - saca prefijo numérico
    - limpia espacios
    """
    n = (name or "").strip()
    n = re.sub(r"^\d+\s*", "", n)  # quita "001 "
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _name_key(name: str) -> str:
    """
    ✅ CLAVE: misma key para DB y CSV:
    - limpia prefijos numéricos tipo "001 "
    - normaliza (acentos, símbolos, espacios)
    """
    return _norm_name(_clean_outlook_name(name or ""))


def _norm_phone(s: Any) -> str:
    if s is None:
        return ""
    if isinstance(s, float):
        if math.isnan(s):
            return ""
        if s.is_integer():
            s = int(s)
    return re.sub(r"\D", "", str(s))


def _same_phone(a: str | None, b: str | None) -> bool:
    aa = _norm_phone(a or "")
    bb = _norm_phone(b or "")
    if not aa or not bb:
        return False
    return aa.endswith(bb) or bb.endswith(aa)


def _phone_key(s: str | None) -> str:
    """Key para mapear rápido: últimos 10 dígitos (o lo que haya)."""
    d = _norm_phone(s or "")
    if not d:
        return ""
    return d[-10:] if len(d) >= 10 else d


def _iter_phones(*phones: Any) -> list[str]:
    out: list[str] = []
    for p in phones:
        d = _norm_phone(p)
        if len(d) >= 7:
            out.append(str(p))
    # dedupe por normalizado
    seen = set()
    uniq: list[str] = []
    for p in out:
        k = _norm_phone(p)
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


# -------------------------
# CSV Reader robusto
# -------------------------

def _read_outlook_file(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(
            path,
            sep=None,
            engine="python",
            dtype=str,
            keep_default_na=False,
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            path,
            sep=None,
            engine="python",
            dtype=str,
            keep_default_na=False,
            encoding="utf-16",
        )

    df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]
    return df


def _get(row: dict, *cols: str) -> str:
    for c in cols:
        if c in row:
            v = row.get(c)
            if v not in (None, ""):
                return str(v)
    return ""


# -------------------------
# Sync principal
# -------------------------

def sync_contactos_from_outlook_csv(
    *,
    session,
    team_id: int,
    csv_path: str,
    dry_run: bool = False,
    debug: bool = True,
) -> dict[str, Any]:
    df = _read_outlook_file(csv_path)

    if debug:
        print("\n[OUTLOOK SYNC] df.columns =", list(df.columns))
        print("[OUTLOOK SYNC] head(2):")
        try:
            print(df.head(2).to_string(index=False))
        except Exception:
            print(df.head(2))

    contactos: list[Contacto] = session.exec(
        select(Contacto).where(Contacto.team_id == team_id)
    ).all()

    chats: list[Chat] = session.exec(
        select(Chat).where(Chat.team_id == team_id)
    ).all()

    # Index por phone_key
    contactos_by_key: dict[str, list[Contacto]] = {}
    for c in contactos:
        for tel in [c.telefono, getattr(c, "telefono2", None)]:
            k = _phone_key(tel)
            if k:
                contactos_by_key.setdefault(k, []).append(c)

    chats_by_key: dict[str, list[Chat]] = {}
    for ch in chats:
        k = _phone_key(ch.numero)
        if k:
            chats_by_key.setdefault(k, []).append(ch)

    # ✅ Index por nombre usando _name_key (FIX)
    contactos_by_name: dict[str, list[Contacto]] = {}
    for c in contactos:
        nk = _name_key(c.nombre)
        if nk:
            contactos_by_name.setdefault(nk, []).append(c)

    if debug:
        # muestra 5 keys para verificar
        sample = list(contactos_by_name.keys())[:5]
        print("\n[OUTLOOK SYNC] sample name keys from DB:", sample)

    stats = {
        "rows": 0,
        "contactos_actualizados": 0,
        "chats_actualizados": 0,
        "sin_match": 0,
        "match_por_tel": 0,
        "match_por_nombre": 0,
        "rows_sin_telefonos": 0,
    }

    for i, row in df.iterrows():
        stats["rows"] += 1
        r = row.to_dict()

        nombre_raw = _get(r, "First Name", "Nombre", "Full Name", "Display Name")
        nombre_csv = _clean_outlook_name(nombre_raw)

        if not nombre_csv:
            continue

        p1 = _get(r, "Phone 1 - Value", "Teléfono 1 - Valor", "Telefono 1 - Valor")
        p2 = _get(r, "Phone 2 - Value", "Teléfono 2 - Valor", "Telefono 2 - Valor")

        phones = _iter_phones(p1, p2)
        if not phones:
            stats["rows_sin_telefonos"] += 1

        if debug and i < 3:
            print(f"\n[OUTLOOK SYNC] Row {i}")
            print("  nombre_raw:", nombre_raw)
            print("  nombre_csv:", nombre_csv)
            print("  name_key:", _name_key(nombre_csv))
            print("  p1:", p1, "| p2:", p2)
            print("  phones(norm):", [_norm_phone(x) for x in phones])

        matched_contacto: Contacto | None = None
        matched_by: str | None = None

        # 1) match por teléfono
        for p in phones:
            k = _phone_key(p)
            if not k:
                continue
            candidatos = contactos_by_key.get(k, [])
            for c in candidatos:
                if _same_phone(c.telefono, p) or _same_phone(getattr(c, "telefono2", None), p):
                    matched_contacto = c
                    matched_by = "tel"
                    break
            if matched_contacto:
                break

        # 2) match por nombre (FIX)
        if not matched_contacto:
            nk = _name_key(nombre_csv)
            candidatos = contactos_by_name.get(nk, [])
            if candidatos:
                candidatos = sorted(
                    candidatos,
                    key=lambda c: (1 if (c.telefono and c.telefono != "desconocido") else 0),
                )
                matched_contacto = candidatos[0]
                matched_by = "nombre"

        if not matched_contacto:
            stats["sin_match"] += 1
            if debug and i < 10:
                print(f"[OUTLOOK SYNC] ❌ sin match: {nombre_csv} phones={phones}")
            continue

        if matched_by == "tel":
            stats["match_por_tel"] += 1
        else:
            stats["match_por_nombre"] += 1

        c = matched_contacto
        changed = False

        # ✅ opcional: normalizar nombre en DB (sacar 001, etc)
        cleaned_db_name = _clean_outlook_name(c.nombre or "")
        if cleaned_db_name and c.nombre != cleaned_db_name:
            if debug:
                print(f"[OUTLOOK SYNC] ✅ clean DB nombre: '{c.nombre}' -> '{cleaned_db_name}'")
            c.nombre = cleaned_db_name
            changed = True

        # Setear teléfono si falta
        if phones:
            p_first = phones[0]
            if (not c.telefono) or c.telefono == "desconocido":
                if debug:
                    print(f"[OUTLOOK SYNC] ✅ set telefono: '{c.telefono}' -> '{p_first}'")
                c.telefono = p_first
                changed = True

            if hasattr(c, "telefono2") and len(phones) >= 2:
                p_second = phones[1]
                if not _same_phone(c.telefono, p_second) and (not getattr(c, "telefono2", None)):
                    if debug:
                        print(f"[OUTLOOK SYNC] ✅ set telefono2 -> '{p_second}'")
                    setattr(c, "telefono2", p_second)
                    changed = True

        if changed:
            stats["contactos_actualizados"] += 1
            session.add(c)

            # ✅ actualizar índices en memoria por si le agregamos teléfono
            for tel in [c.telefono, getattr(c, "telefono2", None)]:
                k = _phone_key(tel)
                if k:
                    contactos_by_key.setdefault(k, []).append(c)

            # ✅ reindex por nombre también si limpiamos nombre
            nk_db = _name_key(c.nombre)
            if nk_db:
                contactos_by_name.setdefault(nk_db, []).append(c)

            # Propagar nombre a chats por teléfono
            for tel in [c.telefono, getattr(c, "telefono2", None)]:
                k = _phone_key(tel)
                if not k:
                    continue
                for ch in chats_by_key.get(k, []):
                    if _same_phone(ch.numero, tel) and ch.nombre != c.nombre:
                        if debug:
                            print(f"[OUTLOOK SYNC] ✅ chat rename: chat#{ch.id} '{ch.nombre}' -> '{c.nombre}'")
                        ch.nombre = c.nombre
                        stats["chats_actualizados"] += 1
                        session.add(ch)

    if not dry_run:
        session.commit()
    else:
        session.rollback()

    if debug:
        print("\n[OUTLOOK SYNC] STATS:", stats)

    return stats
