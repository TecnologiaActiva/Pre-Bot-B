# models/role.py
from sqlmodel import SQLModel, Field
from typing import Optional

class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    descripcion: str | None = None
