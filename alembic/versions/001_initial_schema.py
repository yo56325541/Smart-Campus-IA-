"""Initial schema for SmartCampus AI

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-17 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Déclaration des types Enum
    role_enum = sa.Enum('admin', 'candidat', name='role')
    institution_enum = sa.Enum('IIT', 'ISB', name='institution')

    # 1. Table users
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=120), server_default='', nullable=False),
        sa.Column('role', role_enum, server_default='candidat', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Table programs
    op.create_table(
        'programs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('institution', institution_enum, nullable=False),
        sa.Column('level', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('duration_years', sa.Integer(), nullable=True),
        sa.Column('language', sa.String(length=50), server_default='fr', nullable=False),
        sa.Column('careers', sa.Text(), server_default='', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_programs_slug'), 'programs', ['slug'], unique=True)
    op.create_index(op.f('ix_programs_institution'), 'programs', ['institution'], unique=False)
    op.create_index(op.f('ix_programs_level'), 'programs', ['level'], unique=False)

    # 3. Table admission_conditions
    op.create_table(
        'admission_conditions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('program_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('required_diploma', sa.String(length=120), nullable=True),
        sa.Column('min_average', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admission_conditions_program_id'), 'admission_conditions', ['program_id'], unique=False)

    # 4. Table tariffs
    op.create_table(
        'tariffs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('program_id', sa.Uuid(), nullable=False),
        sa.Column('academic_year', sa.String(length=9), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('registration_fee', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=3), server_default='TND', nullable=False),
        sa.Column('payment_terms', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('program_id', 'academic_year', name='uq_tariffs_program_academic_year')
    )
    op.create_index(op.f('ix_tariffs_program_id'), 'tariffs', ['program_id'], unique=False)

    # 5. Table visitor_sessions
    op.create_table(
        'visitor_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_visitor_sessions_token_hash'), 'visitor_sessions', ['token_hash'], unique=True)
    op.create_index(op.f('ix_visitor_sessions_user_id'), 'visitor_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_visitor_sessions_expires_at'), 'visitor_sessions', ['expires_at'], unique=False)

    # 6. Table conversations
    op.create_table(
        'conversations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=200), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['visitor_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_session_id'), 'conversations', ['session_id'], unique=False)
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)
    op.create_index(op.f('ix_conversations_created_at'), 'conversations', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_conversations_created_at'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_user_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_session_id'), table_name='conversations')
    op.drop_table('conversations')

    op.drop_index(op.f('ix_visitor_sessions_expires_at'), table_name='visitor_sessions')
    op.drop_index(op.f('ix_visitor_sessions_user_id'), table_name='visitor_sessions')
    op.drop_index(op.f('ix_visitor_sessions_token_hash'), table_name='visitor_sessions')
    op.drop_table('visitor_sessions')

    op.drop_index(op.f('ix_tariffs_program_id'), table_name='tariffs')
    op.drop_table('tariffs')

    op.drop_index(op.f('ix_admission_conditions_program_id'), table_name='admission_conditions')
    op.drop_table('admission_conditions')

    op.drop_index(op.f('ix_programs_level'), table_name='programs')
    op.drop_index(op.f('ix_programs_institution'), table_name='programs')
    op.drop_index(op.f('ix_programs_slug'), table_name='programs')
    op.drop_table('programs')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

    # Suppression des types enum si PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        sa.Enum(name='role').drop(bind, checkfirst=True)
        sa.Enum(name='institution').drop(bind, checkfirst=True)
