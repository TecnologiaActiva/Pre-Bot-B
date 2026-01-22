from services.chat_service import importar_chat_controller, get_all_chat, get_only_chat, get_chat_full

def procesar_chat(file, current_user, session):
    return importar_chat_controller(
        file=file,
        team_id=current_user.team_id,
        user_id=current_user.id,
        session=session
    )

def obtener_chats(current_user, session):
    return get_all_chat(
        team_id=current_user.team_id,
        session=session
    )

def obtener_chat(chat_id: int, current_user, session):
    return get_only_chat(
        team_id=current_user.team_id,
        chat_id=chat_id,
        session=session
    )

def obtener_chat_full(chat_id: int, current_user, session):
    return get_chat_full(
        team_id=current_user.team_id,
        chat_id=chat_id,
        session=session
    )