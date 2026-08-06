"""Organization listing endpoint."""

from fastapi import APIRouter

from app.core.dependencies import OrganizationRepositoryDep
from app.models.role import SUPER_ADMIN
from app.schemas.auth import OrganizationRead
from app.security.dependencies import CurrentUser

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get(
    "",
    response_model=list[OrganizationRead],
    summary="List organizations (all, for super_admin; otherwise just your own)",
)
async def list_organizations(
    user: CurrentUser, repository: OrganizationRepositoryDep
) -> list[OrganizationRead]:
    if user.role.name == SUPER_ADMIN:
        organizations = await repository.list_all()
    else:
        organizations = [user.organization]
    return [OrganizationRead.model_validate(org) for org in organizations]
