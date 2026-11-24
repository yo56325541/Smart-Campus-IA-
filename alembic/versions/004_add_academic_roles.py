"""Add academic, interview and direction roles to role enum

Revision ID: 004_add_academic_roles
Revises: 003_academic_interviews_versions
Create Date: 2026-11-24 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '004_add_academic_roles'
down_revision: Union[str, None] = '003_academic_interviews_versions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_ROLES = (
    "responsable_academique_iit",
    "responsable_academique_isb",
    "responsable_entretien",
    "direction",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            for role_val in NEW_ROLES:
                op.execute(sa.text(f"ALTER TYPE role ADD VALUE IF NOT EXISTS '{role_val}'"))


def downgrade() -> None:
    # PostgreSQL ne supporte pas directement ALTER TYPE ... DROP VALUE sans recréation du type enum
    pass
