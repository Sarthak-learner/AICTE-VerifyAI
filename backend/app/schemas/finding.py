"""Pydantic schemas for Findings, Reviews, and Consistency Graph."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.finding import FindingSeverity, FindingStatus


class FindingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    application_id: str
    document_id: Optional[str] = None
    rule_code: str
    rule_name: str
    severity: FindingSeverity
    status: FindingStatus
    title: str
    detail: Optional[str] = None
    page_number: Optional[int] = None
    extracted_value: Optional[str] = None
    expected_value: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    resolution_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FindingListResponse(BaseModel):
    total: int
    open_count: int
    resolved_count: int
    under_review_count: int
    requires_clarification_count: int
    items: List[FindingResponse]


class FindingUpdatePayload(BaseModel):
    status: FindingStatus
    resolution_note: Optional[str] = Field(None, max_length=2000)
    reviewer_label: Optional[str] = Field("Authorized Officer", max_length=255)


class ComparisonItem(BaseModel):
    field: str
    status: str  # "match" | "discrepancy"
    doc_a_id: str
    doc_a_name: str
    doc_a_value: Optional[str] = None
    doc_a_page: Optional[int] = None
    doc_b_id: str
    doc_b_name: str
    doc_b_value: Optional[str] = None
    doc_b_page: Optional[int] = None
    explanation: str
    severity: str


class GraphNode(BaseModel):
    id: str
    type: str  # "document" | "field"
    label: str
    metadata: Optional[Dict[str, Any]] = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str  # "extracted_from" | "consistent" | "discrepancy"
    label: Optional[str] = None


class ConsistencyGraphResponse(BaseModel):
    application_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    comparisons: List[ComparisonItem]
    total_matches: int
    total_discrepancies: int
    evaluated_pairs: int = 0
    has_comparable_fields: bool = False
    explanation: Optional[str] = None
    unprocessed_documents: List[str] = Field(default_factory=list)


class ValidationRunResponse(BaseModel):
    application_id: str
    total_findings: int
    findings: List[FindingResponse]
    consistency_graph: ConsistencyGraphResponse
    message: str
