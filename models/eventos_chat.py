
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class EventoChat(SQLModel, table=True):
    __tablename__ = "eventos_chat"

    id: Optional[int] = Field(default=None, primary_key=True)

    chat_id: int = Field(foreign_key="chat.id")

    mensaje_id: Optional[int] = Field(
        default=None,
        foreign_key="mensaje.id"
    )

    tipo_evento: str
    # Ejemplos:
    # interes | precio | direccion | objecion | cierre | abandono

    descripcion: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
