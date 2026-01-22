from sqlmodel import select, func
from sqlalchemy import case
from models.chat import Chat
from models.mensaje import Mensaje
from models.contactos import Contacto
from models.pipeline_estado import PipelineEstado

ESTADO_CLIENTE = 1

def get_chat_metrics(team_id: int, session):
    # Subquery: 1 contacto por chat (en tu import, todos los mensajes tienen el mismo contacto_id)
    chat_contacto_sq = (
        select(
            Mensaje.chat_id.label("chat_id"),
            func.min(Mensaje.contacto_id).label("contacto_id"),
        )
        .group_by(Mensaje.chat_id)
        .subquery()
    )

    # TOTAL chats
    total = session.exec(
        select(func.count(Chat.id))
        .where(Chat.team_id == team_id)
    ).one()

    # Clientes / No clientes (por contacto.estado)
    clientes = session.exec(
        select(func.count(Chat.id))
        .join(chat_contacto_sq, chat_contacto_sq.c.chat_id == Chat.id)
        .join(Contacto, Contacto.id == chat_contacto_sq.c.contacto_id)
        .where(Chat.team_id == team_id)
        .where(Contacto.estado == ESTADO_CLIENTE)
    ).one()

    no_clientes = session.exec(
        select(func.count(Chat.id))
        .join(chat_contacto_sq, chat_contacto_sq.c.chat_id == Chat.id)
        .join(Contacto, Contacto.id == chat_contacto_sq.c.contacto_id)
        .where(Chat.team_id == team_id)
        .where(Contacto.estado != ESTADO_CLIENTE)
    ).one()

    # Estados pipeline (solo NO clientes)
    rows = session.exec(
        select(PipelineEstado.nombre, func.count(Chat.id))
        .join(Chat, Chat.pipeline_estado_id == PipelineEstado.id)
        .join(chat_contacto_sq, chat_contacto_sq.c.chat_id == Chat.id)
        .join(Contacto, Contacto.id == chat_contacto_sq.c.contacto_id)
        .where(Chat.team_id == team_id)
        .where(Contacto.estado != ESTADO_CLIENTE)
        .group_by(PipelineEstado.nombre)
    ).all()

    pipeline_counts = {nombre: cantidad for (nombre, cantidad) in rows}

    potencial = pipeline_counts.get("Potencial venta", 0)
    interesado = pipeline_counts.get("Interesado", 0)
    perdido = pipeline_counts.get("Perdido", 0)

    # Chats sin pipeline (útil para ver clientes + chats no scoreados)
    sin_pipeline = session.exec(
        select(func.count(Chat.id))
        .where(Chat.team_id == team_id)
        .where(Chat.pipeline_estado_id.is_(None))
    ).one()

    return {
        "total_chats": total,
        "clientes": clientes,
        "no_clientes": no_clientes,
        "potencial_venta": potencial,
        "interesado": interesado,
        "perdido": perdido,
        "sin_pipeline": sin_pipeline,
    }
