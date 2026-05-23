"""drop dead GoPhish columns from phishing_campaigns

Revision ID: b1c2d3e4f5a6
Revises: a3b4c5d6e7f8
Create Date: 2026-05-23

"""
from alembic import op

revision = 'b1c2d3e4f5a6'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('phishing_campaigns', 'gophish_campaign_id')
    op.drop_column('phishing_campaigns', 'gophish_group_id')
    op.drop_column('phishing_campaigns', 'gophish_template_id')
    op.drop_column('phishing_campaigns', 'gophish_page_id')


def downgrade() -> None:
    import sqlalchemy as sa
    op.add_column('phishing_campaigns', sa.Column('gophish_page_id', sa.Integer(), nullable=True))
    op.add_column('phishing_campaigns', sa.Column('gophish_template_id', sa.Integer(), nullable=True))
    op.add_column('phishing_campaigns', sa.Column('gophish_group_id', sa.Integer(), nullable=True))
    op.add_column('phishing_campaigns', sa.Column('gophish_campaign_id', sa.Integer(), nullable=True))
