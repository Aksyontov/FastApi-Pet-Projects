"""empty message

Revision ID: 804dc87dd324
Revises: 856a7b35783a
Create Date: 2024-07-28 16:59:09.105422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '804dc87dd324'
down_revision: Union[str, None] = '856a7b35783a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tweets', sa.Column('has_image', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tweets', 'has_image')
    # ### end Alembic commands ###