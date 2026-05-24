"""Create rssi_consultant_activity_log table

Revision ID: p1q2r3s4t5u6
Revises: o0p1q2r3s4t5
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'p1q2r3s4t5u6'
down_revision = 'o0p1q2r3s4t5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rssi_consultant_activity_log',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('consultant_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('client_id', sa.Integer(),
                  sa.ForeignKey('rssi_clients.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        # view_client | view_sites | view_scans | view_findings | generate_report | send_deliverable | etc.
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('performed_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index(
        'idx_rssi_activity_consultant_date',
        'rssi_consultant_activity_log',
        ['consultant_id', 'performed_at'],
    )
    op.create_index(
        'idx_rssi_activity_client_date',
        'rssi_consultant_activity_log',
        ['client_id', 'performed_at'],
    )


def downgrade():
    op.drop_index('idx_rssi_activity_client_date', table_name='rssi_consultant_activity_log')
    op.drop_index('idx_rssi_activity_consultant_date', table_name='rssi_consultant_activity_log')
    op.drop_table('rssi_consultant_activity_log')
