"""Gated pending-mail onboarding, account consent events and per-user scan attribution."""
from alembic import op
import sqlalchemy as sa
revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('users',sa.Column('registration_pending',sa.Integer(),nullable=False,server_default='0'))
    if op.get_bind().dialect.name=='sqlite':
        # A nullable inline FK can be added directly. Recreating scans in a
        # batch while foreign_keys=ON would cascade-delete dependent reviews.
        op.execute('ALTER TABLE scans ADD COLUMN created_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL')
        op.create_index('ix_scans_created_by','scans',['created_by'])
    else:
        op.add_column('scans',sa.Column('created_by',sa.String(36),nullable=True))
        op.create_foreign_key('fk_scans_created_by','scans','users',['created_by'],['id'],ondelete='SET NULL')
        op.create_index('ix_scans_created_by','scans',['created_by'])
    op.create_table('account_events',sa.Column('id',sa.String(36),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),sa.Column('action',sa.String(100),nullable=False),sa.Column('created_at',sa.Float(),nullable=False))
    op.create_index('ix_account_events_user_id','account_events',['user_id'])

def downgrade():
    op.drop_index('ix_account_events_user_id',table_name='account_events');op.drop_table('account_events')
    op.drop_index('ix_scans_created_by',table_name='scans')
    if op.get_bind().dialect.name!='sqlite':op.drop_constraint('fk_scans_created_by','scans',type_='foreignkey')
    op.drop_column('scans','created_by')
    op.drop_column('users','registration_pending')
