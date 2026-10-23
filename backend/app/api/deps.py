"""Authentication and authorization FastAPI dependencies."""
import logging
from typing import Callable, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services import user_service

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate the JWT Bearer token, returning the User.

    Raises 401 UNAUTHORIZED if token is missing, expired, or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as exc:
        logger.debug("JWT decode failed: %s", exc)
        raise credentials_exception from exc

    user = user_service.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact the system administrator.",
        )
    return current_user


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the authenticated user if valid token is provided, else None."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        email: Optional[str] = payload.get("sub")
        if not email:
            return None
        return user_service.get_user_by_email(db, email=email)
    except Exception:
        return None


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Dependency factory enforcing role-based permissions (RBAC).

    Raises 403 FORBIDDEN if the active user does not have one of the required roles.
    """
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            role_names = [r.value for r in allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Role '{current_user.role.value}' does not have permission "
                    f"for this action. Required: {', '.join(role_names)}."
                ),
            )
        return current_user

    return role_checker


# Convenient role shortcuts
require_admin = require_roles(UserRole.ADMIN)
require_officer_or_admin = require_roles(UserRole.ADMIN, UserRole.OFFICER)
