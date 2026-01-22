# models/archivo.py
from sqlmodel import SQLModel, Field
from typing import Optional

class Archivo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    mensaje_id: int = Field(foreign_key="mensaje.id")

    tipo: str
    filename: str
    path: str
    mime_type: Optional[str] = None
    size: Optional[int] = None
