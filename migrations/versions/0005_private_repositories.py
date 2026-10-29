"""Repository-scoped encrypted private-source credentials; existing repos remain public."""
from alembic import op
import sqlalchemy as sa
revision='0005'
down_revision='0004'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('repositories',sa.Column('source_kind',sa.String(12),nullable=False,server_default='public'))
    op.create_table('repository_credentials',
        sa.Column('repo_id',sa.String(36),sa.ForeignKey('repositories.id',ondelete='CASCADE'),primary_key=True),
        sa.Column('org_id',sa.String(36),sa.ForeignKey('organizations.id',ondelete='CASCADE'),nullable=False),
        sa.Column('ciphertext',sa.Text(),nullable=False),sa.Column('version',sa.Integer(),nullable=False))
    op.create_index('ix_repository_credentials_org_id','repository_credentials',['org_id'])

def downgrade():
    op.drop_index('ix_repository_credentials_org_id',table_name='repository_credentials')
    op.drop_table('repository_credentials')
    op.drop_column('repositories','source_kind')
