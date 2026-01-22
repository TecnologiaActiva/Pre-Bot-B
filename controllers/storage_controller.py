# path: controllers/storage_controller.py

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from models.archivos import Archivo
from models.chat import Chat
from models.mensaje import Mensaje


def obtener_archivo_para_descarga(
    *,
    archivo_id: int,
    team_id: int,
    session: Session,
) -> Archivo:
    """
    Devuelve el Archivo si pertenece al team. Si no, 404.
    Router: arma FileResponse con archivo.path / archivo.mime_type / archivo.filename.
    """
    row = session.exec(
        select(Archivo, Mensaje, Chat)
        .join(Mensaje, Mensaje.id == Archivo.mensaje_id)
        .join(Chat, Chat.id == Mensaje.chat_id)
        .where(Archivo.id == archivo_id)
        .where(Chat.team_id == team_id)
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="Archivo no encontrado o sin permisos")

    archivo, _, _ = row
    return archivo


def listar_archivos_de_chat(
    *,
    chat_id: int,
    team_id: int,
    session: Session,
) -> list[dict]:
    """
    Útil para UI: lista los adjuntos de un chat (con permisos).
    """
    rows = session.exec(
        select(Archivo, Mensaje, Chat)
        .join(Mensaje, Mensaje.id == Archivo.mensaje_id)
        .join(Chat, Chat.id == Mensaje.chat_id)
        .where(Chat.id == chat_id)
        .where(Chat.team_id == team_id)
        .order_by(Mensaje.id.asc(), Archivo.id.asc())
    ).all()

    return [
        {
            "id": a.id,
            "mensaje_id": a.mensaje_id,
            "tipo": a.tipo,
            "filename": a.filename,
            "path": a.path,
            "mime_type": a.mime_type,
            "size": a.size,
        }
        for (a, _, _) in rows
    ]
