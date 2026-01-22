# models/chat_pipeline_historial.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class ChatPipelineHistorial(SQLModel, table=True):
    __tablename__ = "chat_pipeline_historial"

    id: Optional[int] = Field(default=None, primary_key=True)

    chat_id: int = Field(foreign_key="chat.id")
    estado_id: int = Field(foreign_key="pipeline_estado.id")

    changed_at: datetime = Field(default_factory=datetime.utcnow)
