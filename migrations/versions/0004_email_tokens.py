"""Add hashed single-use account email tokens; no existing account state changes."""
from alembic import op
import sqlalchemy as sa
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('email_tokens',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('purpose', sa.String(12), nullable=False),
        sa.Column('expires', sa.Float(), nullable=False),
        sa.Column('consumed_at', sa.Float(), nullable=True))
    op.create_index('ix_email_tokens_user_id', 'email_tokens', ['user_id'])


def downgrade():
    # Disposable test databases only; hosted downgrade requires explicit approval.
    op.drop_index('ix_email_tokens_user_id', table_name='email_tokens')
    op.drop_table('email_tokens')
