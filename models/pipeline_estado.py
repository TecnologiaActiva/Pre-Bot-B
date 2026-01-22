from sqlmodel import SQLModel, Field
from typing import Optional

class PipelineEstado(SQLModel, table=True):
    __tablename__ = "pipeline_estado"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    score_min: int
    score_max: int
