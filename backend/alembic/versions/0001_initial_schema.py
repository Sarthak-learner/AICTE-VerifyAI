"""initial schema — all tables for Prompt 01 + Prompt 02

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-22

Creates all tables for the full application schema including the
Prompt 02 application fields.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # applications table
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reference_number", sa.String(64), nullable=False),
        sa.Column("institution_name", sa.String(512), nullable=False),
        sa.Column("aicte_permanent_id", sa.String(64), nullable=True),
        sa.Column("academic_year", sa.String(10), nullable=True),
        sa.Column("application_category", sa.String(64), nullable=True),
        sa.Column("programme_type", sa.String(64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("institution_type", sa.String(128), nullable=True),
        sa.Column("applicant_name", sa.String(255), nullable=False),
        sa.Column("applicant_email", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "submitted", "under_review", "validation_complete",
                "approved", "rejected",
                name="applicationstatus",
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_officer_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.ForeignKeyConstraint(["assigned_officer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_number"),
    )
    op.create_index("ix_applications_reference_number", "applications", ["reference_number"])

    # documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("stored_filename", sa.String(512), nullable=False),
        sa.Column("document_type", sa.String(128), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("uploaded", "processing", "processed", "failed", name="documentstatus"),
            nullable=False,
        ),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("extracted_fields", sa.Text(), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False),
        sa.Column("duplicate_of_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["duplicate_of_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_application_id", "documents", ["application_id"])
    op.create_index("ix_documents_sha256_hash", "documents", ["sha256_hash"])

    # validation_rules table
    op.create_table(
        "validation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("rule_code", sa.String(64), nullable=False),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_code"),
    )

    # findings table
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("rule_code", sa.String(64), nullable=False),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("info", "warning", "error", name="findingseverity"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("open", "under_review", "resolved", "dismissed", name="findingstatus"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("extracted_value", sa.Text(), nullable=True),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["validation_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # audit_events table
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("actor_label", sa.String(255), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_application_id", "audit_events", ["application_id"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("findings")
    op.drop_table("validation_rules")
    op.drop_table("documents")
    op.drop_table("applications")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS applicationstatus")
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS findingseverity")
    op.execute("DROP TYPE IF EXISTS findingstatus")
