from sqlmodel import select, func
from models.chat import Chat
from models.mensaje import Mensaje
from models.contactos import Contacto

ESTADO_CLIENTE = 1

def get_score_distribution(team_id: int, session):
    # subquery: 1 contacto por chat (min(contacto_id))
    chat_contacto_sq = (
        select(
            Mensaje.chat_id.label("chat_id"),
            func.min(Mensaje.contacto_id).label("contacto_id"),
        )
        .group_by(Mensaje.chat_id)
        .subquery()
    )

    base = (
        select(Chat.id)
        .join(chat_contacto_sq, chat_contacto_sq.c.chat_id == Chat.id)
        .join(Contacto, Contacto.id == chat_contacto_sq.c.contacto_id)
        .where(Chat.team_id == team_id)
        .where(Contacto.estado != ESTADO_CLIENTE)   # ✅ no clientes
    )

    rangos = [
        ("rechazo", Chat.score_actual < 0),
        ("tibio", (Chat.score_actual >= 0) & (Chat.score_actual <= 4)),
        ("interesado", (Chat.score_actual >= 5) & (Chat.score_actual <= 9)),
        ("caliente", Chat.score_actual >= 10),
    ]

    resultado = []
    for nombre, condicion in rangos:
        cantidad = session.exec(
            select(func.count(Chat.id))
            .select_from(Chat)
            .join(chat_contacto_sq, chat_contacto_sq.c.chat_id == Chat.id)
            .join(Contacto, Contacto.id == chat_contacto_sq.c.contacto_id)
            .where(Chat.team_id == team_id)
            .where(Contacto.estado != ESTADO_CLIENTE)
            .where(Chat.score_actual.is_not(None))   # ✅ opcional pero recomendado
            .where(condicion)
        ).one()

        resultado.append({"categoria": nombre, "cantidad": cantidad})

    return resultado
