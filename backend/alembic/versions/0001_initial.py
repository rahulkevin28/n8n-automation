"""Initial FlowForge schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("users", sa.Column("id", sa.String(), primary_key=True), sa.Column("email", sa.String(), nullable=False), sa.Column("password_hash", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("workflows", sa.Column("id", sa.String(), primary_key=True), sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True), sa.Column("name", sa.String(), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("definition", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_workflows_user_id", "workflows", ["user_id"])
    op.create_table("executions", sa.Column("id", sa.String(), primary_key=True), sa.Column("workflow_id", sa.String(), sa.ForeignKey("workflows.id"), nullable=False), sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True), sa.Column("status", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_executions_workflow_id", "executions", ["workflow_id"])
    op.create_index("ix_executions_user_id", "executions", ["user_id"])
    op.create_table("execution_steps", sa.Column("record_id", sa.String(), primary_key=True), sa.Column("step_id", sa.String(), nullable=False), sa.Column("execution_id", sa.String(), sa.ForeignKey("executions.id"), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("output", sa.JSON(), nullable=True), sa.Column("error", sa.Text(), nullable=True))
    op.create_index("ix_execution_steps_execution_id", "execution_steps", ["execution_id"])

def downgrade():
    op.drop_table("execution_steps"); op.drop_table("executions"); op.drop_table("workflows"); op.drop_index("ix_users_email", table_name="users"); op.drop_table("users")
