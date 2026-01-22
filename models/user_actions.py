# models/user_action.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, JSON

class UserAction(SQLModel, table=True):
    __tablename__ = "user_actions"

    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: Optional[int] = Field(default=None, index=True)
    team_id: Optional[int] = Field(default=None, index=True)

    method: str                 # GET, POST, PUT, DELETE
    path: str                   # /procesar, /login, etc
    action: str                 # descripcion corta: "crear_chat", "login"

    payload: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON)
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
