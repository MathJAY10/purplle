"""add transactions

Revision ID: 0003_add_transactions
Revises: 0002_add_retail_fields
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_add_transactions'
down_revision: Union[str, None] = '0002_add_retail_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'transactions',
        sa.Column('transaction_id', sa.String(), nullable=False),
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('basket_value_inr', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('transaction_id')
    )
    op.create_index(op.f('ix_transactions_store_id'), 'transactions', ['store_id'], unique=False)
    op.create_index(op.f('ix_transactions_timestamp'), 'transactions', ['timestamp'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_transactions_timestamp'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_store_id'), table_name='transactions')
    op.drop_table('transactions')
