from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session
from database import get_session
from controllers.chat_controller import procesar_chat, obtener_chats, obtener_chat, obtener_chat_full
from controllers.storage_controller import obtener_archivo_para_descarga, listar_archivos_de_chat
from dependencies.auth import get_current_user
from services.permissions import require_roles
from models.users import User
from controllers.contact_sync_controller import sync_contactos_controller 

router = APIRouter(tags=["Chat"])

@router.post("/procesar")
def procesar(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(1)),
    session: Session = Depends(get_session)
):
    return procesar_chat(file, current_user, session)


@router.get("/chats")
def listar_chats(
    current_user: User = Depends(require_roles(1)),
    session: Session = Depends(get_session)
):
    return obtener_chats(current_user, session)

@router.get("/chats/{chat_id}")
def chat_detalle(
    chat_id: int,
    current_user: User = Depends(require_roles(1)),
    session: Session = Depends(get_session)
):
    return obtener_chat(chat_id, current_user, session)

@router.get("/chats/{chat_id}/full")
def chat_full(
    chat_id: int,
    current_user: User = Depends(require_roles(1)),
    session: Session = Depends(get_session)
):
    return obtener_chat_full(chat_id, current_user, session)


@router.get("/chats/archivos/{archivo_id}")
def descargar_archivo(
    archivo_id: int,
    current_user: User = Depends(require_roles(1)),
    session: Session = Depends(get_session),
):
    team_id = getattr(current_user, "team_id", None)
    if team_id is None:
        raise HTTPException(status_code=500, detail="User sin team_id (ajustar modelo/permiso)")

    archivo = obtener_archivo_para_descarga(
        archivo_id=archivo_id,
        team_id=team_id,
        session=session,
    )

    return FileResponse(
        path=archivo.path,
        media_type=archivo.mime_type or "application/octet-stream",
        filename=archivo.filename,
    )


@router.get("/chats/{chat_id}/archivos")
def archivos_de_chat(
    chat_id: int,
    current_user: User = Depends(require_roles(1)),
    session: Session = Depends(get_session),
):
    team_id = getattr(current_user, "team_id", None)
    if team_id is None:
        raise HTTPException(status_code=500, detail="User sin team_id (ajustar modelo/permiso)")

    return listar_archivos_de_chat(
        chat_id=chat_id,
        team_id=team_id,
        session=session,
    )


##SINCRONIZAR##CONTACTOS##DEOUTLOOK


@router.post("/sync/outlook")
def sync_contacts(
    file: UploadFile = File(...),
    current_user = Depends(require_roles(1)),  # 1=Admin (igual que venís usando)
    session: Session = Depends(get_session),
):
    return sync_contactos_controller(
        file=file,
        team_id=current_user.team_id,
        # user_id=current_user.id,
        session=session,
    )