# models/user.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# models/users.py
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id")
    rol_id: int = Field(foreign_key="role.id")

    nombre: str
    email: str
    password_hash: str
    activo: bool = True
