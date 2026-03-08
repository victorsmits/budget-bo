"""add enrichment_rules table

Revision ID: 2026_03_08_1200
Revises: 2026_03_06_1630
Create Date: 2026-03-08 12:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '2026_03_08_1200'
down_revision: Union[str, None] = '2026_03_06_1630'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    if 'enrichment_rules' in inspector.get_table_names():
        return

    op.create_table(
        'enrichment_rules',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('label_fingerprint', sa.String(length=255), nullable=False),
        sa.Column('merchant_name', sa.String(length=255), nullable=True),
        sa.Column('cleaned_label', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=False, server_default='other'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('learned_from_transaction_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['learned_from_transaction_id'], ['transactions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_enrichment_rules_user_id', 'enrichment_rules', ['user_id'])
    op.create_index('ix_enrichment_rules_label_fingerprint', 'enrichment_rules', ['label_fingerprint'])


def downgrade() -> None:
    op.drop_index('ix_enrichment_rules_label_fingerprint', table_name='enrichment_rules')
    op.drop_index('ix_enrichment_rules_user_id', table_name='enrichment_rules')
    op.drop_table('enrichment_rules')
