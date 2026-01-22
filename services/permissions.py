# path: services/permissions.py
from __future__ import annotations

from typing import Any
from fastapi import Depends, HTTPException

from dependencies.auth import get_current_user
from models.users import User


def require_roles(*allowed_role_ids: int):
    allowed_ids = set(int(x) for x in allowed_role_ids)

    def checker(current_user: User = Depends(get_current_user)):
        if current_user.rol_id not in allowed_ids:
            raise HTTPException(status_code=403, detail="No tenés permisos para esta acción")
        return current_user

    return checker
