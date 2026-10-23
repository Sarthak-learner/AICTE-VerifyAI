"""authenticity_checks table for Prompt 05 screening results

Revision ID: 0002_authenticity_checks
Revises: 0001_initial_schema
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_authenticity_checks"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authenticity_checks",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("check_type", sa.String(64), nullable=False),
        sa.Column("check_name", sa.String(255), nullable=False),
        sa.Column(
            "result",
            sa.Enum("PASS", "REVIEW", "UNAVAILABLE", name="authenticityresult"),
            nullable=False,
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("screening_version", sa.String(32), server_default="1.0.0", nullable=False),
        sa.Column(
            "reviewer_status",
            sa.Enum(
                "open", "under_review", "resolved", "dismissed", "requires_clarification",
                name="findingstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="open",
        ),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_authenticity_checks_application_id", "authenticity_checks", ["application_id"])
    op.create_index("ix_authenticity_checks_document_id", "authenticity_checks", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_authenticity_checks_document_id", table_name="authenticity_checks")
    op.drop_index("ix_authenticity_checks_application_id", table_name="authenticity_checks")
    op.drop_table("authenticity_checks")
    op.execute("DROP TYPE IF EXISTS authenticityresult")
