# legacy single-module router file
# The project has been refactored to use individual routers under
# `backend/routers/*`.  This file remains only for backwards
# compatibility and should not be imported in production code.

from fastapi import APIRouter

router = APIRouter()

@router.get("/deprecated")
def deprecated():
    return {"detail": "Use /auth/register, /users/{id}, etc. instead"}

