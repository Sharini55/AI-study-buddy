"""Baseline schema — initial SunDevil AI tables

This migration captures the full database schema as it exists at the point
Alembic was introduced. Every table created here already exists in production
(SQLite locally); this script brings Postgres into sync from a clean slate.

Revision ID: a1b2c3d4e5f6
Revises:     (none — this is the root migration)
Create Date: 2026-06-10 00:00:00.000000

How to apply
------------
  # First-time Postgres setup:
  export DATABASE_URL="postgresql://user:pass@host/sundevil_prod"
  alembic upgrade head

  # Check current revision in the database:
  alembic current

  # Roll back this migration (drops all tables — destructive!):
  alembic downgrade base
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision metadata
# ---------------------------------------------------------------------------
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None   # root — no parent
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# upgrade() — run when applying this migration
# ---------------------------------------------------------------------------
def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    # Primary table: one row per registered student.
    # `username` is the natural key (lowercase, alphanumeric + underscores).
    # `password_hash` stores a PBKDF2-SHA256 salted signature — never plaintext.
    op.create_table(
        "users",
        sa.Column("username",       sa.String(),   primary_key=True,  nullable=False),
        sa.Column("password_hash",  sa.String(),   nullable=False),
        sa.Column("created_at",     sa.DateTime(), nullable=True),
    )

    # ── workspaces ─────────────────────────────────────────────────────────
    # Each workspace is one subject (e.g., "CSE 230") owned by a user.
    # Cascade rule: deleting a user row removes all their workspaces.
    op.create_table(
        "workspaces",
        sa.Column("id",           sa.String(),  primary_key=True, nullable=False),
        sa.Column("user_id",      sa.String(),  sa.ForeignKey("users.username", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_name", sa.String(),  nullable=False),
        sa.Column("created_at",   sa.DateTime(), nullable=True),
    )
    op.create_index("ix_workspaces_user_id", "workspaces", ["user_id"])

    # ── source_files ───────────────────────────────────────────────────────
    # Extracted + cleaned text from each PDF, PPTX, or pasted source.
    # `file_hash` (SHA-256) enables deduplication on re-upload.
    op.create_table(
        "source_files",
        sa.Column("id",           sa.String(),  primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.String(),  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name",         sa.String(),  nullable=False),
        sa.Column("file_type",    sa.String(),  nullable=False),
        sa.Column("content_text", sa.Text(),    nullable=False),
        sa.Column("file_hash",    sa.String(),  nullable=False),
        sa.Column("created_at",   sa.DateTime(), nullable=True),
    )
    op.create_index("ix_source_files_workspace_id", "source_files", ["workspace_id"])
    op.create_index("ix_source_files_file_hash",    "source_files", ["file_hash"])

    # ── source_images ──────────────────────────────────────────────────────
    # Disk paths for slide images extracted from PPTX files.
    # Binary blobs are stored on disk (Azure Blob / local .storage/),
    # not in the database row, to keep row sizes manageable.
    op.create_table(
        "source_images",
        sa.Column("id",             sa.String(), primary_key=True, nullable=False),
        sa.Column("source_file_id", sa.String(), sa.ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label",          sa.String(), nullable=False),
        sa.Column("storage_path",   sa.String(), nullable=False),
        sa.Column("mime_type",      sa.String(), nullable=False),
    )
    op.create_index("ix_source_images_source_file_id", "source_images", ["source_file_id"])

    # ── study_guides ───────────────────────────────────────────────────────
    # Generated Markdown study guides, one per workspace (latest wins).
    op.create_table(
        "study_guides",
        sa.Column("id",           sa.String(),  primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.String(),  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title",        sa.String(),  nullable=False),
        sa.Column("content_md",   sa.Text(),    nullable=False),
        sa.Column("created_at",   sa.DateTime(), nullable=True),
    )
    op.create_index("ix_study_guides_workspace_id", "study_guides", ["workspace_id"])

    # ── quiz_attempts ──────────────────────────────────────────────────────
    # Historical quiz records: score + full question/answer JSON for replay.
    op.create_table(
        "quiz_attempts",
        sa.Column("id",           sa.String(),  primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.String(),  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score",        sa.Integer(), nullable=False),
        sa.Column("quiz_json",    sa.Text(),    nullable=False),
        sa.Column("answers_json", sa.Text(),    nullable=False),
        sa.Column("created_at",   sa.DateTime(), nullable=True),
    )
    op.create_index("ix_quiz_attempts_workspace_id", "quiz_attempts", ["workspace_id"])


# ---------------------------------------------------------------------------
# downgrade() — run when rolling back this migration
# WARNING: drops all tables and all data. Use only on a clean environment.
# ---------------------------------------------------------------------------
def downgrade() -> None:
    op.drop_table("quiz_attempts")
    op.drop_table("study_guides")
    op.drop_table("source_images")
    op.drop_table("source_files")
    op.drop_table("workspaces")
    op.drop_table("users")
