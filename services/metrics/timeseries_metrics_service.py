# services/metrics/timeseries_metrics_service.py

from datetime import date, datetime, timedelta
from sqlalchemy import case, cast, Date
from sqlmodel import select, func
from models.chat import Chat
from models.mensaje import Mensaje
from models.contactos import Contacto
from models.pipeline_estado import PipelineEstado

ESTADO_CLIENTE = 1

def get_timeseries(team_id: int, session, days: int = 7):
    # rango: hoy inclusive hacia atrás
    end = date.today()
    start = end - timedelta(days=days - 1)

    # 1 contacto por chat (en tu import todos los mensajes tienen el mismo contacto_id)
    chat_contacto_sq = (
        select(
            Mensaje.chat_id.label("chat_id"),
            func.min(Mensaje.contacto_id).label("contacto_id"),
        )
        .group_by(Mensaje.chat_id)
        .subquery()
    )

    day_col = cast(Chat.creado_en, Date)  # funciona bien en Postgres

    rows = session.exec(
        select(
            day_col.label("day"),
            func.sum(case((Contacto.estado == ESTADO_CLIENTE, 1), else_=0)).label("clientes"),
            func.sum(
                case(
                    (
                        (Contacto.estado != ESTADO_CLIENTE) & (PipelineEstado.nombre == "Interesado"),
                        1,
                    ),
                    else_=0,
                )
            ).label("interesado"),
            func.sum(
                case(
                    (
                        (Contacto.estado != ESTADO_CLIENTE) & (PipelineEstado.nombre == "Potencial venta"),
                        1,
                    ),
                    else_=0,
                )
            ).label("potencial_venta"),
            func.sum(
                case(
                    (
                        (Contacto.estado != ESTADO_CLIENTE) & (PipelineEstado.nombre == "Perdido"),
                        1,
                    ),
                    else_=0,
                )
            ).label("perdido"),
        )
        .select_from(Chat)
        .join(chat_contacto_sq, chat_contacto_sq.c.chat_id == Chat.id)
        .join(Contacto, Contacto.id == chat_contacto_sq.c.contacto_id)
        .outerjoin(PipelineEstado, PipelineEstado.id == Chat.pipeline_estado_id)  # clientes suelen tener null
        .where(Chat.team_id == team_id)
        .where(day_col >= start)
        .where(day_col <= end)
        .group_by(day_col)
        .order_by(day_col)
    ).all()

    by_day = {r.day: r for r in rows}

    # rellenar días faltantes con 0
    out = []
    d = start
    while d <= end:
        r = by_day.get(d)
        out.append({
            "date": d.isoformat(),
            "clientes": int(r.clientes) if r else 0,
            "interesado": int(r.interesado) if r else 0,
            "potencial_venta": int(r.potencial_venta) if r else 0,
            "perdido": int(r.perdido) if r else 0,
        })
        d += timedelta(days=1)

    return out
