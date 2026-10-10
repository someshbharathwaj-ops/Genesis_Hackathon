"""User identity endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import RecallException, ResourceNotFoundError
from app.models.identity import User
from app.repositories.user_repo import UserRepository
from app.schemas.identity import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    repo = UserRepository(db)
    existing = await repo.get_by_email(payload.email)
    if existing:
        raise RecallException(
            status_code=status.HTTP_409_CONFLICT,
            code="USER_EMAIL_EXISTS",
            title="User Already Exists",
            detail=f"User with email '{payload.email}' already exists.",
        )
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
    )
    created = await repo.create(user)
    return UserResponse.model_validate(created)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)) -> UserResponse:
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise ResourceNotFoundError("User", user_id)
    return UserResponse.model_validate(user)


@router.get("", response_model=list[UserResponse])
async def list_users(
    limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)
) -> list[UserResponse]:
    repo = UserRepository(db)
    users = await repo.list_all(limit=limit, offset=offset)
    return [UserResponse.model_validate(u) for u in users]
