"""Create rssi_deliverables table

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'q2r3s4t5u6v7'
down_revision = 'p1q2r3s4t5u6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rssi_deliverables',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('client_id', sa.Integer(),
                  sa.ForeignKey('rssi_clients.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('title', sa.String(200), nullable=False),
        # compte_rendu | rapport | recommandation | contrat | autre
        sa.Column('doc_type', sa.String(50), nullable=False, server_default='autre'),
        sa.Column('file_url', sa.String(500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('delivered_at', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
    )


def downgrade():
    op.drop_table('rssi_deliverables')
