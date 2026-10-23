"""Authentication and user management endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    require_admin,
)
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserList, UserResponse
from app.services import user_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT access token",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate user via email and password.

    Accepts JSON body `{"email": "...", "password": "..."}`.
    Returns a signed JWT access token and user metadata.
    """
    user = user_service.authenticate_user(db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact the system administrator.",
        )

    token = create_access_token(
        subject=user.email,
        role=user.role.value,
        user_id=user.id,
    )

    logger.info("User logged in: %s (%s)", user.email, user.role.value)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve current authenticated user profile",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """Return the profile and role of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/seed",
    summary="Seed default demonstration accounts (admin, officer, viewer)",
    status_code=status.HTTP_200_OK,
)
def seed_demo_accounts(
    db: Session = Depends(get_db),
):
    """Seed initial demonstration accounts if they do not exist."""
    seeded = user_service.seed_default_users(db)
    return {
        "status": "ok",
        "seeded_count": len(seeded),
        "accounts": [
            {"email": u["email"], "role": u["role"].value}
            for u in user_service.DEFAULT_USERS
        ],
    }


@router.get(
    "/users",
    response_model=UserList,
    summary="List all users (Admin only)",
)
def list_system_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Return a paginated list of users. Restricted to ADMIN role."""
    items, total = user_service.list_users(db, skip=skip, limit=limit)
    return UserList(
        total=total,
        items=[UserResponse.model_validate(u) for u in items],
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account (Admin only)",
)
def create_system_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new user account with specified role. Restricted to ADMIN role."""
    existing = user_service.get_user_by_email(db, email=payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{payload.email}' already exists.",
        )
    user = user_service.create_user(db, payload)
    return UserResponse.model_validate(user)
