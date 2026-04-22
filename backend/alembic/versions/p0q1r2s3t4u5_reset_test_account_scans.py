"""Reset scans for test account rocherdavid@ymail.com

Revision ID: p0q1r2s3t4u5
Revises: o9p0q1r2s3t4
Create Date: 2026-04-22

One-off data reset for the test account so the free plan
1-scan limit can be verified from a clean state.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "p0q1r2s3t4u5"
down_revision: Union[str, None] = "o9p0q1r2s3t4"
branch_labels = None
depends_on = None

TEST_EMAIL = "rocherdavid@ymail.com"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        DELETE FROM scans
        WHERE site_id IN (
            SELECT s.id FROM sites s
            JOIN users u ON s.user_id = u.id
            WHERE u.email = :email
        )
    """), {"email": TEST_EMAIL})


def downgrade() -> None:
    pass
