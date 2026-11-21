"""Add applications table (SA-13)

Revision ID: 002_applications
Revises: 001_initial_schema
Create Date: 2026-11-21 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_applications'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Création idempotente du type ENUM applicationstatus (IF NOT EXISTS)
    bind.execute(sa.text(
        "CREATE TYPE IF NOT EXISTS applicationstatus "
        "AS ENUM ('draft', 'submitted', 'under_review', 'accepted', 'rejected')"
    ))

    # Création idempotente de la table applications
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS applications (
            id          UUID        NOT NULL,
            user_id     UUID        NOT NULL,
            program_id  UUID        NOT NULL,
            academic_year VARCHAR(9) NOT NULL,
            status      applicationstatus NOT NULL DEFAULT 'draft',
            notes       TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id),
            CONSTRAINT uq_applications_user_program_year
                UNIQUE (user_id, program_id, academic_year),
            CONSTRAINT applications_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT applications_program_id_fkey
                FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE
        )
    """))

    # Index (IF NOT EXISTS est supporté sur PostgreSQL 9.5+)
    bind.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_applications_user_id    ON applications (user_id)"
    ))
    bind.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_applications_program_id ON applications (program_id)"
    ))
    bind.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_applications_academic_year ON applications (academic_year)"
    ))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DROP TABLE IF EXISTS applications"))
    if bind.dialect.name == 'postgresql':
        bind.execute(sa.text("DROP TYPE IF EXISTS applicationstatus"))
