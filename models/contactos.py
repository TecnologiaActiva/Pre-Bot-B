# models/contactos.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Contacto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id")

    nombre: str
    telefono: Optional[str] = None
    username: Optional[str] = None
    estado : int

    created_at: datetime = Field(default_factory=datetime.utcnow)
