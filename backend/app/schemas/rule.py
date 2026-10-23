"""Pydantic schemas for Validation Rules."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: Optional[str] = None
    code: str
    name: str
    description: Optional[str] = None
    applies_to_document_type: Optional[str] = None
    severity: str
    is_active: bool
    is_demo: bool
    parameters: Optional[Dict[str, Any]] = None


class RuleListResponse(BaseModel):
    total: int
    items: List[RuleResponse]
