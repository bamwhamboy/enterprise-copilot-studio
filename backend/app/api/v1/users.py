"""Current-user endpoint."""

from fastapi import APIRouter

from app.schemas.auth import UserRead
from app.security.dependencies import CurrentUser

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead, summary="Get the authenticated user's profile")
async def get_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
