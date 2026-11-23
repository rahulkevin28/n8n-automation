"""Persist workflow step attempt counts."""

from alembic import op
import sqlalchemy as sa


revision = "0002_execution_step_attempts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "execution_steps",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("execution_steps", "attempts")
