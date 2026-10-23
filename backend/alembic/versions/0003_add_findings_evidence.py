"""add evidence and review fields to findings

Revision ID: 0003_add_findings_evidence
Revises: 0002_authenticity_checks
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_add_findings_evidence"
down_revision = "0002_authenticity_checks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add evidence JSON column for structured supporting details
    op.add_column("findings", sa.Column("evidence", sa.JSON(), nullable=True))

    # Add resolved_by_id for reviewer audit attribution
    op.add_column(
        "findings",
        sa.Column(
            "resolved_by_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
    )

    # Add resolution_note for officer review assessment notes
    op.add_column("findings", sa.Column("resolution_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("findings", "resolution_note")
    op.drop_column("findings", "resolved_by_id")
    op.drop_column("findings", "evidence")
