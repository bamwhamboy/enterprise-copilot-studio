"""Role listing endpoint."""

from fastapi import APIRouter

from app.core.dependencies import RoleRepositoryDep
from app.schemas.auth import RoleRead
from app.security.dependencies import CurrentUser

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=list[RoleRead], summary="List available roles")
async def list_roles(user: CurrentUser, repository: RoleRepositoryDep) -> list[RoleRead]:
    roles = await repository.list_all()
    return [RoleRead.model_validate(role) for role in roles]
