"""Authentication schemas for login, token response, and token payload."""
from typing import Optional
from pydantic import BaseModel

from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None
