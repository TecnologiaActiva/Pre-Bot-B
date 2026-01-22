# path: routes/user_routes.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

import models
from database import get_session
from services.permissions import require_roles
from services.security import hash_password

router = APIRouter(prefix="/users", tags=["Users"])

class UserOut(BaseModel):
    id: int
    team_id: int
    rol_id: int
    nombre: str
    email: str
    activo: bool

class CreateUserRequest(BaseModel):
    rol_id: int
    nombre: str
    email: EmailStr
    password: str

@router.get("", response_model=list[UserOut])
def list_users(
    current_user = Depends(require_roles(1)),  # Admin
    session: Session = Depends(get_session),
):
    users = session.exec(
        select(models.User)
        .where(models.User.team_id == current_user.team_id)
        .order_by(models.User.id.desc())
    ).all()

    return [
        UserOut(
            id=u.id,
            team_id=u.team_id,
            rol_id=u.rol_id,
            nombre=u.nombre,
            email=u.email,
            activo=bool(u.activo),
        )
        for u in users
    ]

@router.post("", response_model=UserOut)
def create_user(
    data: CreateUserRequest,
    current_user = Depends(require_roles(1)),  # Admin
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(models.User).where(models.User.email == data.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya existe")

    role = session.get(models.Role, data.rol_id)
    if not role:
        raise HTTPException(status_code=400, detail="Rol inválido")

    user = models.User(
        team_id=current_user.team_id,  # ✅ fuerza team del admin logueado
        rol_id=data.rol_id,
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        activo=True,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return UserOut(
        id=user.id,
        team_id=user.team_id,
        rol_id=user.rol_id,
        nombre=user.nombre,
        email=user.email,
        activo=bool(user.activo),
    )
