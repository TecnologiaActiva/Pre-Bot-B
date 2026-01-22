from services.metrics.chat_metrics_service import get_chat_metrics
from services.metrics.pipeline_metrics_service import get_pipeline_metrics
from services.metrics.score_metrics_service import get_score_distribution
from services.metrics.chat_list_service import get_chats_by_categoria

def obtener_metricas(team_id, session):
    return {
        "general": get_chat_metrics(team_id, session),
        "pipeline": get_pipeline_metrics(team_id, session),
        "score": get_score_distribution(team_id, session)
    }


def obtener_chats_por_categoria(*, team_id: int, session, categoria: str, q: str | None, limit: int, offset: int):
    return get_chats_by_categoria(
        team_id=team_id,
        session=session,
        categoria=categoria,
        q=q,
        limit=limit,
        offset=offset,
    )