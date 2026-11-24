"""Candidatures, documents, sync logs and conversation messages

Revision ID: 002_candidatures_documents_messages
Revises: 001_initial_schema
Create Date: 2026-11-21 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002_candidatures_docs_msgs'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enums
    application_status_enum = sa.Enum('draft', 'submitted', 'under_review', 'accepted', 'rejected', name='application_status')
    document_type_enum = sa.Enum('diplome', 'releve_notes', 'cin', 'cv', 'autre', name='document_type')
    sync_status_enum = sa.Enum('in_progress', 'success', 'failed', name='sync_status')
    message_role_enum = sa.Enum('user', 'assistant', 'system', name='message_role')

    # 2. Table messages (SA-26, SA-36, SA-37)
    op.create_table(
        'messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('conversation_id', sa.Uuid(), nullable=False),
        sa.Column('role', message_role_enum, server_default='user', nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_created_at'), 'messages', ['created_at'], unique=False)

    # 3. Table applications (SA-13)
    op.create_table(
        'applications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('program_id', sa.Uuid(), nullable=False),
        sa.Column('academic_year', sa.String(length=9), nullable=False),
        sa.Column('status', application_status_enum, server_default='draft', nullable=False),
        sa.Column('notes', sa.Text(), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'program_id', 'academic_year', name='uq_user_program_academic_year')
    )
    op.create_index(op.f('ix_applications_user_id'), 'applications', ['user_id'], unique=False)
    op.create_index(op.f('ix_applications_program_id'), 'applications', ['program_id'], unique=False)
    op.create_index(op.f('ix_applications_academic_year'), 'applications', ['academic_year'], unique=False)
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'], unique=False)

    # 4. Table documents (SA-14)
    op.create_table(
        'documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=True),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('document_type', document_type_enum, server_default='autre', nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), server_default='', nullable=False),
        sa.Column('mime_type', sa.String(length=100), server_default='application/octet-stream', nullable=False),
        sa.Column('file_size', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_application_id'), 'documents', ['application_id'], unique=False)
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)
    op.create_index(op.f('ix_documents_document_type'), 'documents', ['document_type'], unique=False)

    # 5. Table sync_logs (SA-14)
    op.create_table(
        'sync_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('status', sync_status_enum, server_default='in_progress', nullable=False),
        sa.Column('records_synced', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sync_logs_entity_type'), 'sync_logs', ['entity_type'], unique=False)
    op.create_index(op.f('ix_sync_logs_status'), 'sync_logs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sync_logs_status'), table_name='sync_logs')
    op.drop_index(op.f('ix_sync_logs_entity_type'), table_name='sync_logs')
    op.drop_table('sync_logs')

    op.drop_index(op.f('ix_documents_document_type'), table_name='documents')
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_application_id'), table_name='documents')
    op.drop_table('documents')

    op.drop_index(op.f('ix_applications_status'), table_name='applications')
    op.drop_index(op.f('ix_applications_academic_year'), table_name='applications')
    op.drop_index(op.f('ix_applications_program_id'), table_name='applications')
    op.drop_index(op.f('ix_applications_user_id'), table_name='applications')
    op.drop_table('applications')

    op.drop_index(op.f('ix_messages_created_at'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_table('messages')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        sa.Enum(name='message_role').drop(bind, checkfirst=True)
        sa.Enum(name='sync_status').drop(bind, checkfirst=True)
        sa.Enum(name='document_type').drop(bind, checkfirst=True)
        sa.Enum(name='application_status').drop(bind, checkfirst=True)
