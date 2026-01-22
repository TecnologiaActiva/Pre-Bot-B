from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class ChatScoreEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    chat_id: int = Field(foreign_key="chat.id")

    origen: str      # rule | human | ia
    motivo: str      # "Pidió precio", "Confirmó instalación"
    delta: int       # +2, +5, -3

    creado_en: datetime = Field(default_factory=datetime.utcnow)
