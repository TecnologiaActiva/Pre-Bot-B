from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from database import get_session
from dependencies.auth import get_current_user
from controllers.metrics_controller import obtener_metricas, obtener_chats_por_categoria
from services.permissions import require_roles
from services.metrics.timeseries_metrics_service import get_timeseries

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.get("/chats/dashboard")
def metrics_chats(
    current_user = Depends(require_roles(1)),
    session: Session = Depends(get_session)
):
    return obtener_metricas(
        team_id=current_user.team_id,
        session=session
    )


@router.get("/chats/timeseries")
def metrics_timeseries(
    days: int = Query(7, ge=1, le=365),
    current_user = Depends(require_roles(1)),
    session: Session = Depends(get_session),
):
    return get_timeseries(team_id=current_user.team_id, session=session, days=days)

@router.get("/chats/list")
def metrics_chats_list(
    categoria: str = Query(..., description="interesado | potencial_venta | perdido | cliente | no_cliente"),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_roles(1)),
    session: Session = Depends(get_session),
):
    return obtener_chats_por_categoria(
        team_id=current_user.team_id,
        session=session,
        categoria=categoria,
        q=q,
        limit=limit,
        offset=offset,
    )