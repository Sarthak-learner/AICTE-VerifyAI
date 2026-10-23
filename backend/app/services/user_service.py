"""User service: manages user persistence, authentication, and seed accounts."""
import logging
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)

DEFAULT_USERS = [
    {
        "email": "admin@aicte.gov.in",
        "full_name": "AICTE System Administrator",
        "role": UserRole.ADMIN,
        "password": "Admin@123",
    },
    {
        "email": "officer@aicte.gov.in",
        "full_name": "Verification Officer Sharma",
        "role": UserRole.OFFICER,
        "password": "Officer@123",
    },
    {
        "email": "viewer@aicte.gov.in",
        "full_name": "Public Auditor Verma",
        "role": UserRole.VIEWER,
        "password": "Viewer@123",
    },
]


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Retrieve a user by lowercase email address."""
    return db.execute(
        select(User).where(func.lower(User.email) == email.lower().strip())
    ).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Retrieve a user by ID."""
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def create_user(db: Session, user_in: UserCreate) -> User:
    """Create a new user with hashed password."""
    user = User(
        email=user_in.email.lower().strip(),
        full_name=user_in.full_name.strip(),
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def list_users(db: Session, skip: int = 0, limit: int = 50) -> tuple[list[User], int]:
    """List users paginated."""
    total = db.scalar(select(func.count(User.id))) or 0
    items = list(
        db.execute(
            select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
        ).scalars().all()
    )
    return items, total


def seed_default_users(db: Session) -> list[User]:
    """Seed standard prototype users (admin, officer, viewer) if not already present."""
    seeded = []
    for u_data in DEFAULT_USERS:
        existing = get_user_by_email(db, u_data["email"])
        if not existing:
            user = User(
                email=u_data["email"],
                full_name=u_data["full_name"],
                role=u_data["role"],
                hashed_password=hash_password(u_data["password"]),
                is_active=True,
            )
            db.add(user)
            seeded.append(user)
            logger.info("Seeded default %s user: %s", u_data["role"].value, u_data["email"])
    if seeded:
        db.commit()
        for u in seeded:
            db.refresh(u)
    return seeded
