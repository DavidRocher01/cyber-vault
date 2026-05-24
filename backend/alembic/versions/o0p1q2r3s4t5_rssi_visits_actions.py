"""Create rssi_visits and rssi_actions tables

Revision ID: o0p1q2r3s4t5
Revises: n9o0p1q2r3s4
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'o0p1q2r3s4t5'
down_revision = 'n9o0p1q2r3s4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rssi_visits',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column(
            'client_id', sa.Integer(),
            sa.ForeignKey('rssi_clients.id', ondelete='CASCADE'),
            nullable=False, index=True,
        ),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('visit_type', sa.String(30), nullable=False, server_default='monthly'),
        sa.Column('location', sa.String(20), nullable=False, server_default='onsite'),
        sa.Column('status', sa.String(20), nullable=False, server_default='planned'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('actual_date', sa.Date(), nullable=True),
        sa.Column('duration_hours', sa.Numeric(4, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_rssi_visits_scheduled_date', 'rssi_visits', ['scheduled_date'])

    op.create_table(
        'rssi_actions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column(
            'client_id', sa.Integer(),
            sa.ForeignKey('rssi_clients.id', ondelete='CASCADE'),
            nullable=False, index=True,
        ),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('assigned_to', sa.String(50), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'source_visit_id', sa.Integer(),
            sa.ForeignKey('rssi_visits.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_rssi_actions_status', 'rssi_actions', ['status'])


def downgrade():
    op.drop_table('rssi_actions')
    op.drop_table('rssi_visits')
