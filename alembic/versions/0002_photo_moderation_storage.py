"""Add private object storage keys and explicit photo moderation status

Revision ID: 0002_storage
Revises: 0001_v8
"""
from alembic import op
import sqlalchemy as sa
revision="0002_storage";down_revision="0001_v8";branch_labels=None;depends_on=None

def upgrade():
    op.add_column("profile_photos", sa.Column("storage_key", sa.String(255), nullable=True))
    op.add_column("profile_photos", sa.Column("content_type", sa.String(40), nullable=True))
    op.add_column("profile_photos", sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"))
    op.add_column("verifications", sa.Column("storage_key", sa.String(255), nullable=True))

def downgrade():
    op.drop_column("verifications", "storage_key")
    op.drop_column("profile_photos", "status")
    op.drop_column("profile_photos", "content_type")
    op.drop_column("profile_photos", "storage_key")
