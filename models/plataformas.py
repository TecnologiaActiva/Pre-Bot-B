# models/plataforma.py
from sqlmodel import SQLModel, Field
from typing import Optional

class Plataforma(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str  # whatsapp | telegram | etc
