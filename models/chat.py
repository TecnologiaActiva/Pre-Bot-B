# models/chat.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Chat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    team_id: int = Field(foreign_key="team.id")

    nombre: str
    numero: str

    score_actual: int = 0
    pipeline_estado_id: Optional[int] = Field(default=None, foreign_key="pipeline_estado.id")

    creado_en: datetime = Field(default_factory=datetime.utcnow)
