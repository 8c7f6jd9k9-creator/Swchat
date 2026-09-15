"""Add next_attempt_at to outbox for real retry/backoff scheduling

Revision ID: 0003_outbox_backoff
Revises: 0002_storage
"""
from alembic import op
import sqlalchemy as sa
revision="0003_outbox_backoff";down_revision="0002_storage";branch_labels=None;depends_on=None

def upgrade():
    op.add_column("outbox", sa.Column("next_attempt_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))

def downgrade():
    op.drop_column("outbox", "next_attempt_at")
