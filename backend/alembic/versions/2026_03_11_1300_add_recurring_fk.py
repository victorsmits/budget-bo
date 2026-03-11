"""Add recurring_expense_id foreign key on transactions

Revision ID: 2026_03_11_1300
Revises: 2026_03_08_1500
Create Date: 2026-03-11 13:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "2026_03_11_1300"
down_revision: Union[str, None] = "2026_03_08_1500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if not _column_exists("transactions", "recurring_expense_id"):
        op.add_column(
            "transactions",
            sa.Column("recurring_expense_id", UUID(as_uuid=True), nullable=True),
        )
        op.create_index(
            "ix_transactions_recurring_expense_id",
            "transactions",
            ["recurring_expense_id"],
            unique=False,
        )
        op.create_foreign_key(
            "fk_transactions_recurring_expense_id",
            "transactions",
            "recurring_expenses",
            ["recurring_expense_id"],
            ["id"],
        )


def downgrade() -> None:
    if _column_exists("transactions", "recurring_expense_id"):
        op.drop_constraint(
            "fk_transactions_recurring_expense_id",
            "transactions",
            type_="foreignkey",
        )
        op.drop_index("ix_transactions_recurring_expense_id", table_name="transactions")
        op.drop_column("transactions", "recurring_expense_id")
