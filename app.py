from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import SQLModel, Session, select
from dependencies.auth import get_current_user
from database import engine, get_session
from services.security import (
    verify_password,
    create_access_token,
    hash_password
)

# 👇 IMPORT CLAVE: registra TODOS los modelos
import models

# Routers
from routes.chat_routes import router as chat_router
from routes.mensaje_routes import router as mensaje_router
from routes.metrics_routes import router as metrics_routes
from routes.user_routes import router as user_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,   # 👈 clave
    allow_methods=["*"],
    allow_headers=["*"],
)



# -------------------------
# STARTUP
# -------------------------
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


# -------------------------
# ROOT
# -------------------------
@app.get("/")
def home():
    return {"mensaje": "Backend listo 🚀"}


# -------------------------
# ROUTERS
# -------------------------
app.include_router(chat_router)
app.include_router(mensaje_router)
app.include_router(metrics_routes)
app.include_router(user_router)

# =========================
# AUTH 
# =========================

class LoginRequest(BaseModel):
    email: str
    password: str



@app.post("/login")
def login(
    data: LoginRequest,
    response: Response,
    session: Session = Depends(get_session)
):
    user = session.exec(
        select(models.User).where(models.User.email == data.email)
    ).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = create_access_token({
        "sub": str(user.id),           # 👈 importante: string
        "team_id": user.team_id,
        "email": user.email,
        "rol_id": user.rol_id,
        "nombre": user.nombre
    })

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,      # True en prod (HTTPS)
        samesite="none",    # prod cross-site => "none" + secure=True
        max_age=60 * 60 * 8,
        path="/",
    )

    return {"ok": True}


@app.get("/me")
def me(current_user=Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "rol_id": current_user.rol_id, "nombre": current_user.nombre}


@app.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


# =========================
# DEV ONLY – CREATE USER
# =========================

class CreateUserRequest(BaseModel):
    team_id: int
    rol_id: int
    nombre: str
    email: str
    password: str


@app.post("/dev/create-user")
def dev_create_user(
    data: CreateUserRequest,
    session: Session = Depends(get_session)
):
    existing = session.exec(
        select(models.User).where(models.User.email == data.email)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="El email ya existe"
        )
        
         # 2️⃣ Verificar rol válido
    role = session.get(models.Role, data.rol_id)
    if not role:
        raise HTTPException(
            status_code=400,
            detail="Rol inválido"
        )

    user = models.User(
        team_id=data.team_id,
        rol_id = data.rol_id,
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password)
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "team_id": user.team_id,
        "rol": role.nombre
    }
