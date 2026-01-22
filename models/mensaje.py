# models/mensaje.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Mensaje(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    chat_id: int = Field(foreign_key="chat.id", nullable=False)
    contacto_id: int = Field(foreign_key="contacto.id", nullable=False)

    # 1 = texto | 2 = img | 3 = archivo | 4 = audio
    tipo: int = Field(default=1, nullable=False)

    texto: Optional[str] = Field(default=None)

    # ✅ quien figura en el TXT antes del ":" (tal cual)
    autor_raw: Optional[str] = Field(default=None)

    # ✅ clave UI
    from_me: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
