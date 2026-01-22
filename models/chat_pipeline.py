from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class ChatPipeline(SQLModel, table=True):
    __tablename__ = "chat_pipeline"

    chat_id: int = Field(
        foreign_key="chat.id",
        primary_key=True
    )

    estado_id: int = Field(
        foreign_key="pipeline_estado.id"
    )

    updated_at: datetime = Field(default_factory=datetime.utcnow)
