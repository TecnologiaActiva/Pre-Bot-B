# path: services/chat_service.py

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlmodel import select

from models.archivos import Archivo
from models.chat import Chat
from models.contactos import Contacto
from models.mensaje import Mensaje
from models.chat_score_event import ChatScoreEvent
from models.pipeline_estado import PipelineEstado

from parser import parsear_chat
from services.chat_scoring_service import aplicar_score, calcular_score_chat
from services.parserwsp import classify_whatsapp_filename
from services.storage_service import index_extracted_files, resolve_message_attachments, store_media_file
import re
import unicodedata
from sqlalchemy import func


DEFAULT_TIPO_TEXTO = "text"
DEFAULT_TIPO_MEDIA = "media"

TIPO_TEXTO = 1
TIPO_IMG = 2
TIPO_ARCHIVO = 3
TIPO_AUDIO = 4

SYSTEM_PATTERNS = [
    "los mensajes y las llamadas están cifrados",
    "cambió tu código de seguridad",
    "tocá para obtener más información",
]


def _norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize(
        "NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _norm_phone(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _is_system_line(texto: str) -> bool:
    t = (texto or "").strip().lower()
    return any(p in t for p in SYSTEM_PATTERNS)


def _is_from_me(*, autor: str, peer_nombre: str, peer_tel: str | None) -> bool:
    # si autor coincide con el contacto del chat => NO es mío
    a_name = _norm_name(autor)
    p_name = _norm_name(peer_nombre)

    if a_name and p_name and a_name == p_name:
        return False

    a_phone = _norm_phone(autor)
    p_phone = _norm_phone(peer_tel or "")
    # a veces viene con +549... y tu contacto “corto”
    if a_phone and p_phone and (a_phone.endswith(p_phone) or p_phone.endswith(a_phone)):
        return False

    # si no coincide con el contacto => asumimos que es de tu lado (empresa)
    return True


def _same_phone(a: str | None, b: str | None) -> bool:
    aa = _norm_phone(a or "")
    bb = _norm_phone(b or "")
    if not aa or not bb:
        return False
    return aa.endswith(bb) or bb.endswith(aa)


def _find_existing_chat(
    session,
    *,
    team_id: int,
    nombre_contacto: str,
    telefono_contacto: str | None,
) -> Chat | None:
    tel_norm = _norm_phone(telefono_contacto or "")
    chat: Chat | None = None

    # 1) buscar por teléfono (si sirve)
    if tel_norm and tel_norm != _norm_phone("desconocido"):
        suffix = tel_norm[-8:]  # últimos 8 dígitos para achicar candidatos

        candidatos = session.exec(
            select(Chat)
            .where(Chat.team_id == team_id)
            .where(Chat.numero.like(f"%{suffix}%"))
        ).all()

        for c in candidatos:
            if _same_phone(c.numero, telefono_contacto):
                return c

    # 2) fallback por nombre (cuando numero = desconocido)
    nombre_norm = _norm_name(nombre_contacto)
    if nombre_norm:
        # traemos candidatos por team y comparamos normalizado (sin DB column)
        candidatos = session.exec(
            select(Chat).where(Chat.team_id == team_id)
        ).all()

        for c in candidatos:
            if _norm_name(c.nombre) == nombre_norm:
                return c

    return None


def _pick_message_tipo(texto: str, attachment_paths: list[str]) -> int:
    if not attachment_paths:
        return TIPO_TEXTO

    t = (texto or "").lower()
    # heurística rápida si whatsapp pone "<Multimedia omitido>"
    if "audio" in t or "ptt" in t or "opus" in t:
        return TIPO_AUDIO
    if "img" in t or "foto" in t or "imagen" in t:
        return TIPO_IMG
    return TIPO_ARCHIVO


def upsert_contacto(
    session,
    *,
    team_id: int,
    nombre: str,
    telefono: str | None,
    estado: int,
) -> Contacto:
    if telefono:
        existing = session.exec(
            select(Contacto)
            .where(Contacto.team_id == team_id)
            .where(Contacto.telefono == telefono)
        ).first()
    else:
        existing = session.exec(
            select(Contacto)
            .where(Contacto.team_id == team_id)
            .where(Contacto.nombre == nombre)
        ).first()

    if existing:
        existing.estado = estado
        if telefono and not existing.telefono:
            existing.telefono = telefono
        if nombre and existing.nombre != nombre:
            existing.nombre = nombre
        session.add(existing)
        return existing

    contacto = Contacto(
        team_id=team_id,
        estado=estado,
        nombre=nombre,
        telefono=telefono,
        username=None,
    )
    session.add(contacto)
    return contacto


def importar_chat_controller(file, team_id: int, user_id: int, session) -> dict[str, Any]:
    nombre_contacto, telefono_contacto, estado_contacto = classify_whatsapp_filename(
        file.filename)

    workdir = tempfile.mkdtemp(prefix="wsp_import_")
    upload_path = os.path.join(workdir, os.path.basename(file.filename))

    try:
        with open(upload_path, "wb") as f:
            f.write(file.file.read())

        with zipfile.ZipFile(upload_path, "r") as zip_ref:
            zip_ref.extractall(workdir)
            chat_txt = next(
                (os.path.join(workdir, n)
                 for n in zip_ref.namelist() if n.lower().endswith(".txt")),
                None,
            )

        if not chat_txt:
            raise HTTPException(
                status_code=400, detail="No se encontró archivo .txt en el ZIP")
        extracted_index = index_extracted_files(
            workdir, chat_txt_path=chat_txt)
        mensajes = parsear_chat(chat_txt)

        contacto = upsert_contacto(
            session,
            team_id=team_id,
            nombre=nombre_contacto,
            telefono=telefono_contacto,
            estado=estado_contacto,
        )
        session.commit()
        session.refresh(contacto)

        chat = _find_existing_chat(
            session,
            team_id=team_id,
            nombre_contacto=nombre_contacto,
            telefono_contacto=telefono_contacto,
        )

        if not chat:
            chat = Chat(
                nombre=nombre_contacto,
                numero=telefono_contacto or "desconocido",
                team_id=team_id,
                creado_por=user_id,
            )
            session.add(chat)
            session.commit()
            session.refresh(chat)
        else:
            # opcional: si antes estaba "desconocido" y ahora vino número, lo actualizo
            if (chat.numero == "desconocido" or not chat.numero) and telefono_contacto and telefono_contacto != "desconocido":
                chat.numero = telefono_contacto
                session.add(chat)
                session.commit()

                extracted_index = index_extracted_files(
                    workdir, chat_txt_path=chat_txt)

        archivos_guardados = 0
        mensajes_guardados = 0
        texto_cliente_para_score: list[str] = []
        for m in mensajes:
            texto = (m.get("mensaje") or "").strip()
            autor = (m.get("usuario") or "").strip()

            # si no hay autor o es línea sistema => saltar
            if not autor:
                if _is_system_line(texto):
                    continue
                continue

            if _is_system_line(texto):
                continue

            # fecha/hora
            if m.get("fecha") and m.get("hora"):
                created_at = datetime.strptime(
                    f"{m['fecha']} {m['hora']}", "%d/%m/%Y %H:%M")
            else:
                created_at = datetime.utcnow()

            # ✅ adjuntos (NO lo dejes comentado)
            attachment_paths = resolve_message_attachments(
                message_text=texto,
                extracted_index=extracted_index,
            ) or []

            # ✅ dedupe manteniendo orden
            attachment_paths = list(dict.fromkeys(attachment_paths))

            # from_me
            from_me = _is_from_me(
                autor=autor,
                peer_nombre=nombre_contacto,
                peer_tel=telefono_contacto,
            )
            if not from_me and texto:
                texto_cliente_para_score.append(texto.lower())
            msg = Mensaje(
                chat_id=chat.id,
                contacto_id=contacto.id,
                tipo=_pick_message_tipo(texto, attachment_paths),
                texto=texto,
                autor_raw=autor,
                from_me=from_me,
                created_at=created_at,
            )
            session.add(msg)
            session.flush()  # para tener msg.id
            mensajes_guardados += 1

            # ✅ por si un mismo archivo aparece repetido en el texto
            stored_cache: dict[str, Any] = {}

            for src in attachment_paths:
                if src in stored_cache:
                    stored = stored_cache[src]
                else:
                    try:
                        stored = store_media_file(
                            src_path=src, team_id=team_id, chat_id=chat.id)
                    except FileNotFoundError:
                        # si el zip no trae ese archivo, no tires toda la importación
                        continue
                    stored_cache[src] = stored

                # ✅ ESTE add VA DENTRO DEL LOOP
                session.add(
                    Archivo(
                        mensaje_id=msg.id,
                        tipo=stored.tipo,
                        filename=stored.filename,
                        path=stored.path,
                        mime_type=stored.mime_type,
                        size=stored.size,
                    )
                )
                archivos_guardados += 1

        # ✅ commit UNA sola vez al final
        session.commit()

        # ✅ score y commit al final
        ESTADO_CLIENTE = 1  # ajustá según tu sistema
        if estado_contacto == ESTADO_CLIENTE:
            chat.pipeline_estado_id = None  # opcional
            session.add(chat)
            session.commit()
            return {
                "chat_id": chat.id,
                "mensajes_guardados": mensajes_guardados,
                "archivos_guardados": archivos_guardados,
                "score_eventos": 0,
                "score_actual": chat.score_actual,
                "contacto_estado": estado_contacto,
                "contacto_telefono": telefono_contacto,
                "contacto_nombre": nombre_contacto,
                "score_skipped": True,
            }

        # ✅ calcular score solo con texto del cliente
        mensajes_cliente = [{"mensaje": t} for t in texto_cliente_para_score]
        eventos = calcular_score_chat(mensajes_cliente)
        aplicar_score(chat, eventos, session)
        session.commit()

        return {
            "chat_id": chat.id,
            "mensajes_guardados": mensajes_guardados,
            "archivos_guardados": archivos_guardados,
            "score_eventos": len(eventos),
            "score_actual": chat.score_actual,
            "contacto_estado": estado_contacto,
            "contacto_telefono": telefono_contacto,
            "contacto_nombre": nombre_contacto,
        }

    finally:
        shutil.rmtree(workdir, ignore_errors=True)

def descargar_archivo_controller(*, archivo_id: int, team_id: int, session) -> Archivo:
    """
    Valida que el archivo pertenezca al team:
    Archivo -> Mensaje -> Chat.team_id
    """
    row = session.exec(
        select(Archivo, Mensaje, Chat)
        .join(Mensaje, Mensaje.id == Archivo.mensaje_id)
        .join(Chat, Chat.id == Mensaje.chat_id)
        .where(Archivo.id == archivo_id)
        .where(Chat.team_id == team_id)
    ).first()

    if not row:
        raise HTTPException(
            status_code=404, detail="Archivo no encontrado o sin permisos")

    archivo, _, _ = row
    return archivo


def get_all_chat(team_id: int, session) -> list[dict[str, Any]]:
    # Subquery: 1 contacto por chat
    chat_contacto_sq = (
        select(
            Mensaje.chat_id.label("chat_id"),
            func.min(Mensaje.contacto_id).label("contacto_id"),
        )
        .group_by(Mensaje.chat_id)
        .subquery()
    )

    # Subquery: último mensaje por chat (USANDO created_at)
    last_msg_sq = (
        select(
            Mensaje.chat_id.label("chat_id"),
            func.max(Mensaje.created_at).label("last_message_at"),
        )
        .group_by(Mensaje.chat_id)
        .subquery()
    )

    rows = session.exec(
        select(Chat, Contacto, last_msg_sq.c.last_message_at)
        .join(chat_contacto_sq, chat_contacto_sq.c.chat_id == Chat.id)
        .join(Contacto, Contacto.id == chat_contacto_sq.c.contacto_id)
        .join(last_msg_sq, last_msg_sq.c.chat_id == Chat.id)
        .where(Chat.team_id == team_id)
        .order_by(last_msg_sq.c.last_message_at.desc())
    ).all()

    return [
        {
            "id": chat.id,
            "nombre": chat.nombre,
            "numero": chat.numero,
            "telefono": contacto.telefono,
            "telefono2": contacto.telefono2,
            # 🔥 fecha del ÚLTIMO mensaje
            "fecha_carga": (
                last_message_at.isoformat()
                if last_message_at
                else None
            ),
        }
        for chat, contacto, last_message_at in rows
    ]


def get_only_chat(team_id: int, session, chat_id: int) -> dict[str, Any]:
    chat = session.exec(
        select(Chat).where(Chat.id == chat_id).where(Chat.team_id == team_id)
    ).first()

    if not chat:
        raise HTTPException(
            status_code=404, detail="Chat no encontrado o sin permisos")

    return {
        "id": chat.id,
        "nombre": chat.nombre,
        "numero": chat.numero,
        "score_actual": chat.score_actual,
        "pipeline_estado_id": chat.pipeline_estado_id,
        "creado_en": chat.creado_en.isoformat(),
        "creado_por": chat.creado_por,
        "team_id": chat.team_id,
    }


def get_chat_full(team_id: int, chat_id: int, session) -> dict[str, Any]:
    chat = session.exec(
        select(Chat).where(Chat.id == chat_id).where(Chat.team_id == team_id)
    ).first()

    if not chat:
        raise HTTPException(
            status_code=404, detail="Chat no encontrado o sin permisos")

    mensajes = session.exec(
        select(Mensaje).where(Mensaje.chat_id ==
                              chat_id).order_by(Mensaje.created_at.asc())
    ).all()

    score_events = session.exec(
        select(ChatScoreEvent)
        .where(ChatScoreEvent.chat_id == chat_id)
        .order_by(ChatScoreEvent.creado_en.asc())
    ).all()

    pipeline = None
    if chat.pipeline_estado_id:
        pipeline = session.exec(
            select(PipelineEstado).where(
                PipelineEstado.id == chat.pipeline_estado_id)
        ).first()

    return {
        "chat": {
            "id": chat.id,
            "nombre": chat.nombre,
            "numero": chat.numero,
            "score_actual": chat.score_actual,
            "pipeline": {"id": pipeline.id, "nombre": pipeline.nombre} if pipeline else None,
            "creado_en": chat.creado_en.isoformat(),
            "team_id": chat.team_id,
        },
        "mensajes": [
            {
                "id": m.id,
                "contacto_id": m.contacto_id,
                "autor_raw": m.autor_raw,
                "from_me": m.from_me,
                "texto": m.texto,
                "tipo": m.tipo,
                "created_at": m.created_at.isoformat(),
            }
            for m in mensajes
        ],
        "score_events": [
            {
                "id": e.id,
                "origen": e.origen,
                "motivo": e.motivo,
                "delta": e.delta,
                "creado_en": e.creado_en.isoformat(),
            }
            for e in score_events
        ],
    }
