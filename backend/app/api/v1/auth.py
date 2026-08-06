"""Authentication endpoints.

POST /login uses OAuth2PasswordRequestForm (form-encoded username/
password, not JSON) specifically because that's what makes Swagger's
built-in "Authorize" button work out of the box -- it POSTs exactly
this shape to the URL configured in oauth2_scheme's tokenUrl.
"""

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.dependencies import AuthServiceDep
from app.schemas.auth import RefreshRequest, TokenResponse, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (creates or joins an organization)",
)
async def register(payload: UserRegister, service: AuthServiceDep) -> UserRead:
    user = await service.register(payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="Log in and receive tokens")
async def login(
    service: AuthServiceDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    # OAuth2PasswordRequestForm's field is literally called "username";
    # this application authenticates by email, so form_data.username IS
    # the email address.
    return await service.login(form_data.username, form_data.password)


@router.post(
    "/refresh", response_model=TokenResponse, summary="Exchange a refresh token for new tokens"
)
async def refresh(payload: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a refresh token")
async def logout(payload: RefreshRequest, service: AuthServiceDep) -> None:
    await service.logout(payload.refresh_token)
