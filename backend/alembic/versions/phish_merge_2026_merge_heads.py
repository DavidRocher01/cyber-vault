"""merge phishing target events branch into main

Revision ID: phish_merge_2026
Revises: aa0b1c2d3e4f, phish_target_ts_2026
Create Date: 2026-05-27

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'phish_merge_2026'
down_revision: Union[str, tuple] = ('aa0b1c2d3e4f', 'phish_target_ts_2026')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
