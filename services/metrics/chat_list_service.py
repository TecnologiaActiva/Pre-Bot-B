# path: services/metrics/chat_list_service.py

from __future__ import annotations

from sqlmodel import select, func
from models.chat import Chat
from models.mensaje import Mensaje
from models.contactos import Contacto
from models.pipeline_estado import PipelineEstado

ESTADO_CLIENTE = 1

# Subquery: 1 contacto por chat (en tu import, todos los mensajes tienen el mismo contacto_id)
def _chat_contacto_sq():
    return (
        select(
            Mensaje.chat_id.label("chat_id"),
            func.min(Mensaje.contacto_id).label("contacto_id"),
        )
        .group_by(Mensaje.chat_id)
        .subquery()
    )

def get_chats_by_categoria(
    *,
    team_id: int,
    session,
    categoria: str,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    categoria = (categoria or "").strip().lower()

    cc = _chat_contacto_sq()

    stmt = (
        select(
            Chat.id,
            Chat.nombre,
            Chat.numero,
            Chat.score_actual,
            Chat.creado_en,
            PipelineEstado.nombre.label("pipeline"),
            Contacto.estado.label("contacto_estado"),
        )
        .select_from(Chat)
        .join(cc, cc.c.chat_id == Chat.id)
        .join(Contacto, Contacto.id == cc.c.contacto_id)
        .outerjoin(PipelineEstado, PipelineEstado.id == Chat.pipeline_estado_id)
        .where(Chat.team_id == team_id)
    )

    # ✅ filtros por categoría
    if categoria in {"interesado", "potencial_venta", "perdido"}:
        # solo NO clientes
        stmt = stmt.where(Contacto.estado != ESTADO_CLIENTE)

        # nombres EXACTOS como los cargaste en pipeline_estado
        map_pipeline = {
            "interesado": "Interesado",
            "potencial_venta": "Potencial venta",
            "perdido": "Perdido",  # o "No interesado" si así lo guardaste
        }
        stmt = stmt.where(PipelineEstado.nombre == map_pipeline[categoria])

    elif categoria in {"no_cliente", "no-clientes", "no_clientes"}:
        stmt = stmt.where(Contacto.estado != ESTADO_CLIENTE)

    elif categoria in {"cliente", "clientes"}:
        stmt = stmt.where(Contacto.estado == ESTADO_CLIENTE)

    else:
        # por default: no rompas, devolvé no clientes
        stmt = stmt.where(Contacto.estado != ESTADO_CLIENTE)

    # ✅ búsqueda
    if q:
        qq = f"%{q.strip()}%"
        stmt = stmt.where((Chat.nombre.ilike(qq)) | (Chat.numero.ilike(qq)))

    # ✅ total (count) con subquery
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.exec(count_stmt).one()

    # ✅ orden + paginación
    stmt = stmt.order_by((Chat.score_actual).desc().nullslast(), Chat.creado_en.desc())
    stmt = stmt.offset(offset).limit(limit)

    rows = session.exec(stmt).all()

    items = [
        {
            "id": r.id,
            "nombre": r.nombre,
            "numero": r.numero,
            "score_actual": r.score_actual or 0,
            "creado_en": r.creado_en.isoformat() if r.creado_en else None,
            "pipeline": r.pipeline,
            "contacto_estado": r.contacto_estado,
        }
        for r in rows
    ]

    return {
        "categoria": categoria,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }
