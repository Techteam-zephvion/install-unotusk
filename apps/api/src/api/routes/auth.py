from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.dependencies.database import get_db
from apps.api.src.models.user import User
from apps.api.src.schemas.auth import TokenResponse
from apps.api.src.schemas.user import UserCreate, UserLogin, UserRead
from apps.api.src.services.auth_service import AuthService
from apps.api.src.services.org_service import OrgService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await AuthService.signup(db, data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await AuthService.login(db, data)


@router.get("/me", response_model=dict)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    orgs = await OrgService.list_user_organizations(db, current_user.id)
    return {
        "user": UserRead.model_validate(current_user),
        "organizations": orgs,
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
) -> dict:
    return {"status": "ok", "message": "Successfully logged out"}
