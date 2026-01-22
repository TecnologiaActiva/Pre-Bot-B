from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from controllers.mensaje_controller import leer_mensaje
from dependencies.auth import get_current_user
from models.users import User
from services.permissions import require_roles

router = APIRouter(tags=["Mensajes"])

@router.get("/mensajes/{chat_id}")
def mensajes(
    chat_id: int,
    current_user: User = Depends(require_roles(1)),
    session: Session = Depends(get_session)
):
    return leer_mensaje(chat_id, current_user, session)
