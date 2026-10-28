"""Opt-in manual retention; existing data and policies are untouched."""
from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('retention_policies',sa.Column('org_id',sa.String(36),sa.ForeignKey('organizations.id',ondelete='CASCADE'),primary_key=True),sa.Column('days',sa.Integer(),nullable=True),sa.Column('version',sa.Integer(),nullable=False),sa.Column('updated_at',sa.Float(),nullable=False))
    op.create_table('cleanup_runs',sa.Column('id',sa.String(36),primary_key=True),sa.Column('org_id',sa.String(36),sa.ForeignKey('organizations.id',ondelete='CASCADE'),nullable=False),sa.Column('actor_id',sa.String(36),nullable=False),sa.Column('policy_version',sa.Integer(),nullable=False),sa.Column('cutoff',sa.Float(),nullable=False),sa.Column('scan_ids',sa.Text(),nullable=False),sa.Column('created_at',sa.Float(),nullable=False),sa.Column('expires_at',sa.Float(),nullable=False),sa.Column('status',sa.String(24),nullable=False),sa.Column('deleted_count',sa.Integer(),nullable=False),sa.Column('preserved_count',sa.Integer(),nullable=False),sa.Column('reason',sa.Text(),nullable=False))
    op.create_index('ix_cleanup_runs_org_id','cleanup_runs',['org_id'])

def downgrade():
    # Disposable test DBs only; deleting retention audit records in staging requires approval.
    op.drop_index('ix_cleanup_runs_org_id',table_name='cleanup_runs')
    op.drop_table('cleanup_runs')
    op.drop_table('retention_policies')
