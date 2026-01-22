from sqlmodel import select
from fastapi import HTTPException
from models.chat import Chat
from models.mensaje import Mensaje


def obtener_mensajes(chat_id: int, current_user, session):
    # 1️⃣ Validar acceso al chat
    chat = session.exec(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.team_id == current_user.team_id
        )
    ).first()

    if not chat:
        raise HTTPException(
            status_code=403,
            detail="No tenés acceso a este chat"
        )

    # 2️⃣ Traer mensajes
    mensajes = session.exec(
        select(Mensaje)
        .where(
            Mensaje.chat_id == chat_id,
            Mensaje.team_id == current_user.team_id
        )
        .order_by(Mensaje.fecha)
    ).all()

    return mensajes
