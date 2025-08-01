"""Create logs table"""

from alembic import op
import sqlalchemy as sa


revision = "20251105_01"
down_revision = "20251010_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("target", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table("logs")

