"""Per-scan finding decisions and API append-only decision history."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None


def columns():
    return [sa.Column('scan_id',sa.String(36),sa.ForeignKey('scans.id',ondelete='CASCADE'),nullable=False),
            sa.Column('finding_id',sa.String(128),nullable=False),
            sa.Column('version',sa.Integer(),nullable=False),
            sa.Column('status',sa.String(24),nullable=False),
            sa.Column('reason',sa.Text(),nullable=False),
            sa.Column('expires_at',sa.Float(),nullable=True),
            sa.Column('actor_id',sa.String(36),nullable=False),
            sa.Column('updated_at',sa.Float(),nullable=False)]


def upgrade():
    op.create_table('finding_reviews',*columns(),sa.PrimaryKeyConstraint('scan_id','finding_id'))
    op.create_table('finding_review_events',sa.Column('id',sa.String(36),primary_key=True),*columns(),sa.UniqueConstraint('scan_id','finding_id','version'))
    op.create_index('ix_finding_review_events_scan_id','finding_review_events',['scan_id'])


def downgrade():
    # Only run on disposable test databases or with an explicitly approved data-loss plan.
    op.drop_index('ix_finding_review_events_scan_id',table_name='finding_review_events')
    op.drop_table('finding_review_events')
    op.drop_table('finding_reviews')
