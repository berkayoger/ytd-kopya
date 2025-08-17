"""create admin_test_runs table"""

from alembic import op
import sqlalchemy as sa


revision = "20251201_01"
down_revision = "20251105_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_test_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("suite", sa.String(), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=False),
        sa.Column("summary_raw", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table("admin_test_runs")

