from sqlmodel import select, func
from models.chat import Chat
from models.mensaje import Mensaje
from models.contactos import Contacto
from models.pipeline_estado import PipelineEstado

ESTADO_CLIENTE = 1

def get_pipeline_metrics(team_id: int, session):
    chat_contacto_sq = (
        select(
            Mensaje.chat_id.label("chat_id"),
            func.min(Mensaje.contacto_id).label("contacto_id"),
        )
        .group_by(Mensaje.chat_id)
        .subquery()
    )

    rows = session.exec(
        select(PipelineEstado.nombre, func.count(Chat.id))
        .join(Chat, Chat.pipeline_estado_id == PipelineEstado.id)
        .join(chat_contacto_sq, chat_contacto_sq.c.chat_id == Chat.id)
        .join(Contacto, Contacto.id == chat_contacto_sq.c.contacto_id)
        .where(Chat.team_id == team_id)
        .where(Contacto.estado != ESTADO_CLIENTE) 
        .group_by(PipelineEstado.nombre)
    ).all()

    return [{"estado": nombre, "cantidad": cantidad} for nombre, cantidad in rows]
