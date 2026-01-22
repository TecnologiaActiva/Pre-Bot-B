from services.mensaje_service import obtener_mensajes

def leer_mensaje(chat_id, current_user, session):
    return obtener_mensajes(
        chat_id=chat_id,
        current_user=current_user,
        session=session
    )
