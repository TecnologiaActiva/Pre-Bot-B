from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str

    created_at: datetime = Field(default_factory=datetime.utcnow)
    activo: bool = True
