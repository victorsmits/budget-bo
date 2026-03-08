"""add drinking transaction category enum value

Revision ID: 2026_03_08_1700
Revises: 2026_03_08_1500
Create Date: 2026-03-08 17:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2026_03_08_1700"
down_revision: Union[str, None] = "2026_03_08_1500"
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
    _add_enum_value_if_missing("transactioncategory", "DRINKING")


def downgrade() -> None:
    pass
