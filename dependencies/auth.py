# path: dependencies/auth.py
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlmodel import Session, select

from database import get_session
from models.users import User
from services.security import SECRET_KEY, ALGORITHM

COOKIE_NAME = "access_token"


def _get_token(request: Request) -> str | None:
    # 1) Cookie (modo recomendado)
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token

    # 2) Bearer (compatibilidad / Postman)
    auth = request.headers.get("Authorization")
    if auth:
        parts = auth.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()

    return None


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_raw = payload.get("sub")
        if not user_id_raw:
            raise HTTPException(status_code=401, detail="Token inválido")

        user_id = int(user_id_raw)
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user or not user.activo:
        raise HTTPException(status_code=401, detail="Usuario inválido")

    return user
