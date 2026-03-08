"""add missing transactioncategory enum values

Revision ID: 2026_03_08_1500
Revises: 2026_03_08_1200
Create Date: 2026-03-08 15:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2026_03_08_1500"
down_revision: Union[str, None] = "2026_03_08_1200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_enum_value_if_missing(enum_name: str, value: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = '{enum_name}'
                  AND e.enumlabel = '{value}'
            ) THEN
                ALTER TYPE {enum_name} ADD VALUE '{value}';
            END IF;
        END$$;
        """
    )


def upgrade() -> None:
    # Existing enum values are persisted as enum labels (member names), not .value strings.
    _add_enum_value_if_missing("transactioncategory", "GROCERIES")
    _add_enum_value_if_missing("transactioncategory", "DINING")
    _add_enum_value_if_missing("transactioncategory", "HOME_IMPROVEMENT")


def downgrade() -> None:
    # PostgreSQL enum values cannot be dropped safely in-place.
    # Keep downgrade as no-op to avoid destructive type recreation.
    pass
