"""Add server_default to updated_at column.

Revision ID: 2b1ec534a2b9
Revises: 03f338454ea8
Create Date: 2024-08-31 01:05:35.588072

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "2b1ec534a2b9"
down_revision = "03f338454ea8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Alter the 'updated_at' column to include server_default
    op.alter_column(
        "users",
        "updated_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        existing_server_default=None,
        server_onupdate=sa.text("now()"),
        nullable=False,
    )


def downgrade() -> None:
    # Revert the column to its previous state
    op.alter_column(
        "users",
        "updated_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_server_default="now()",
        server_onupdate=sa.text("now()"),
        nullable=False,
    )
