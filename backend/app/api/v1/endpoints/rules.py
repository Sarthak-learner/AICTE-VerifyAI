"""Validation rules listing endpoint."""
from fastapi import APIRouter, Depends
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.rule import RuleListResponse, RuleResponse
from app.services.validation.default_rules import DEFAULT_RULES

router = APIRouter()


@router.get(
    "",
    response_model=RuleListResponse,
    summary="List configurable validation rules",
)
def get_validation_rules(
    current_user: User = Depends(get_current_active_user),
):
    """Returns the list of configured validation rules and illustrative demo thresholds."""
    items = [
        RuleResponse(
            code=r["code"],
            name=r["name"],
            description=r.get("description"),
            applies_to_document_type=r.get("applies_to_document_type"),
            severity=r["severity"],
            is_active=r["is_active"],
            is_demo=r["is_demo"],
            parameters=r.get("parameters"),
        )
        for r in DEFAULT_RULES
    ]
    return RuleListResponse(total=len(items), items=items)
