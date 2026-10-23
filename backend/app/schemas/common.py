"""Shared Pydantic schema utilities."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    disclaimer: str
