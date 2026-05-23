"""add_phishing_tables

Revision ID: l7m8n9o0p1q2
Revises: k6l7m8n9o0p1
Create Date: 2026-05-20 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'l7m8n9o0p1q2'
down_revision: Union[str, None] = 'k6l7m8n9o0p1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'phishing_campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('plan_tier', sa.String(length=50), nullable=False, server_default='standard'),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('domain_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('scenario_keys', sa.Text(), nullable=True),
        sa.Column('gophish_campaign_id', sa.Integer(), nullable=True),
        sa.Column('gophish_group_id', sa.Integer(), nullable=True),
        sa.Column('gophish_template_id', sa.Integer(), nullable=True),
        sa.Column('gophish_page_id', sa.Integer(), nullable=True),
        sa.Column('targets_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('emails_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('opened_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('clicked_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('submitted_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cgu_accepted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_phishing_campaigns_id'), 'phishing_campaigns', ['id'], unique=False)
    op.create_index(op.f('ix_phishing_campaigns_user_id'), 'phishing_campaigns', ['user_id'], unique=False)
    op.create_index(op.f('ix_phishing_campaigns_status'), 'phishing_campaigns', ['status'], unique=False)

    op.create_table(
        'phishing_targets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['phishing_campaigns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_phishing_targets_id'), 'phishing_targets', ['id'], unique=False)
    op.create_index(op.f('ix_phishing_targets_campaign_id'), 'phishing_targets', ['campaign_id'], unique=False)

    op.create_table(
        'phishing_domain_verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('verification_token', sa.String(length=255), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_phishing_domain_verifications_id'), 'phishing_domain_verifications', ['id'], unique=False)
    op.create_index(op.f('ix_phishing_domain_verifications_user_id'), 'phishing_domain_verifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_phishing_domain_verifications_domain'), 'phishing_domain_verifications', ['domain'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_phishing_domain_verifications_domain'), table_name='phishing_domain_verifications')
    op.drop_index(op.f('ix_phishing_domain_verifications_user_id'), table_name='phishing_domain_verifications')
    op.drop_index(op.f('ix_phishing_domain_verifications_id'), table_name='phishing_domain_verifications')
    op.drop_table('phishing_domain_verifications')

    op.drop_index(op.f('ix_phishing_targets_campaign_id'), table_name='phishing_targets')
    op.drop_index(op.f('ix_phishing_targets_id'), table_name='phishing_targets')
    op.drop_table('phishing_targets')

    op.drop_index(op.f('ix_phishing_campaigns_status'), table_name='phishing_campaigns')
    op.drop_index(op.f('ix_phishing_campaigns_user_id'), table_name='phishing_campaigns')
    op.drop_index(op.f('ix_phishing_campaigns_id'), table_name='phishing_campaigns')
    op.drop_table('phishing_campaigns')
