"""Academic details, specialties, courses, equivalences, interviews, and document versions

Revision ID: 003_academic_interviews_versions
Revises: 002_candidatures_docs_msgs
Create Date: 2026-11-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '003_academic_interviews_versions'
down_revision: Union[str, None] = '002_candidatures_docs_msgs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enums
    equivalence_status_enum = sa.Enum('pending', 'under_review', 'approved', 'rejected', name='equivalence_status')
    interview_type_enum = sa.Enum('en_ligne', 'presentiel', name='interview_type')
    interview_status_enum = sa.Enum('programme', 'confirme', 'effectue', 'annule', name='interview_status')
    jury_decision_enum = sa.Enum('favorable', 'defavorable', 'liste_attente', name='jury_decision')
    vector_sync_action_enum = sa.Enum('upsert', 'delete', name='vector_sync_action')
    vector_sync_status_enum = sa.Enum('pending', 'processing', 'completed', 'failed', name='vector_sync_status')

    # 2. Table specialties (SA-12)
    op.create_table(
        'specialties',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('program_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_specialties_program_id'), 'specialties', ['program_id'], unique=False)
    op.create_index(op.f('ix_specialties_code'), 'specialties', ['code'], unique=False)

    # 3. Table courses (SA-12 - Matières enseignées)
    op.create_table(
        'courses',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('program_id', sa.Uuid(), nullable=False),
        sa.Column('specialty_id', sa.Uuid(), nullable=True),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('semester', sa.String(length=10), nullable=False),
        sa.Column('credits_ects', sa.Numeric(precision=4, scale=1), server_default='3.0', nullable=False),
        sa.Column('coefficient', sa.Numeric(precision=4, scale=2), server_default='1.50', nullable=False),
        sa.Column('hours_lectures', sa.Integer(), server_default='21', nullable=False),
        sa.Column('hours_tutorials', sa.Integer(), server_default='21', nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['specialty_id'], ['specialties.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_courses_program_id'), 'courses', ['program_id'], unique=False)
    op.create_index(op.f('ix_courses_specialty_id'), 'courses', ['specialty_id'], unique=False)
    op.create_index(op.f('ix_courses_code'), 'courses', ['code'], unique=False)
    op.create_index(op.f('ix_courses_semester'), 'courses', ['semester'], unique=False)

    # 4. Table academic_profiles (SA-13)
    op.create_table(
        'academic_profiles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('bac_section', sa.String(length=100), server_default='', nullable=False),
        sa.Column('bac_year', sa.Integer(), nullable=True),
        sa.Column('bac_average', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('highest_diploma', sa.String(length=150), server_default='', nullable=False),
        sa.Column('graduation_institution', sa.String(length=200), server_default='', nullable=False),
        sa.Column('graduation_year', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_academic_profile_user_id')
    )
    op.create_index(op.f('ix_academic_profiles_user_id'), 'academic_profiles', ['user_id'], unique=True)

    # 5. Table equivalences (SA-13)
    op.create_table(
        'equivalences',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('target_program_id', sa.Uuid(), nullable=False),
        sa.Column('source_diploma', sa.String(length=200), nullable=False),
        sa.Column('source_institution', sa.String(length=200), nullable=False),
        sa.Column('source_country', sa.String(length=100), server_default='Tunisie', nullable=False),
        sa.Column('requested_level', sa.String(length=50), nullable=False),
        sa.Column('status', equivalence_status_enum, server_default='pending', nullable=False),
        sa.Column('decision_notes', sa.Text(), server_default='', nullable=False),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_equivalences_user_id'), 'equivalences', ['user_id'], unique=False)
    op.create_index(op.f('ix_equivalences_target_program_id'), 'equivalences', ['target_program_id'], unique=False)
    op.create_index(op.f('ix_equivalences_status'), 'equivalences', ['status'], unique=False)

    # 6. Table interviews (SA-13)
    op.create_table(
        'interviews',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), server_default='30', nullable=False),
        sa.Column('interview_type', interview_type_enum, server_default='en_ligne', nullable=False),
        sa.Column('location_or_link', sa.String(length=300), server_default='', nullable=False),
        sa.Column('status', interview_status_enum, server_default='programme', nullable=False),
        sa.Column('interviewer_id', sa.Uuid(), nullable=True),
        sa.Column('notes', sa.Text(), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id', name='uq_interviews_application_id')
    )
    op.create_index(op.f('ix_interviews_application_id'), 'interviews', ['application_id'], unique=True)
    op.create_index(op.f('ix_interviews_scheduled_at'), 'interviews', ['scheduled_at'], unique=False)
    op.create_index(op.f('ix_interviews_status'), 'interviews', ['status'], unique=False)

    # 7. Table interview_results (SA-13)
    op.create_table(
        'interview_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('interview_id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('technical_score', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('motivation_score', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('language_score', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('overall_score', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('decision', jury_decision_enum, server_default='favorable', nullable=False),
        sa.Column('jury_feedback', sa.Text(), server_default='', nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id', name='uq_interview_results_application_id'),
        sa.UniqueConstraint('interview_id', name='uq_interview_results_interview_id')
    )
    op.create_index(op.f('ix_interview_results_application_id'), 'interview_results', ['application_id'], unique=True)
    op.create_index(op.f('ix_interview_results_interview_id'), 'interview_results', ['interview_id'], unique=True)
    op.create_index(op.f('ix_interview_results_decision'), 'interview_results', ['decision'], unique=False)

    # 8. Colonne current_version sur documents (SA-14)
    op.add_column('documents', sa.Column('current_version', sa.Integer(), server_default='1', nullable=False))

    # 9. Table document_versions (SA-14)
    op.create_table(
        'document_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('version_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), server_default='0', nullable=False),
        sa.Column('change_summary', sa.String(length=255), server_default='Dépôt initial', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_versions_document_id'), 'document_versions', ['document_id'], unique=False)

    # 10. Table vector_sync_tasks (SA-14 - Traitements automatiques base vectorielle)
    op.create_table(
        'vector_sync_tasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=True),
        sa.Column('action', vector_sync_action_enum, server_default='upsert', nullable=False),
        sa.Column('status', vector_sync_status_enum, server_default='pending', nullable=False),
        sa.Column('embedding_model', sa.String(length=100), server_default='text-embedding-3-small', nullable=False),
        sa.Column('collection_name', sa.String(length=100), server_default='smartcampus_documents', nullable=False),
        sa.Column('chunk_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('vector_dimensions', sa.Integer(), server_default='1536', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vector_sync_tasks_document_id'), 'vector_sync_tasks', ['document_id'], unique=False)
    op.create_index(op.f('ix_vector_sync_tasks_status'), 'vector_sync_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_vector_sync_tasks_action'), 'vector_sync_tasks', ['action'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_vector_sync_tasks_action'), table_name='vector_sync_tasks')
    op.drop_index(op.f('ix_vector_sync_tasks_status'), table_name='vector_sync_tasks')
    op.drop_index(op.f('ix_vector_sync_tasks_document_id'), table_name='vector_sync_tasks')
    op.drop_table('vector_sync_tasks')

    op.drop_index(op.f('ix_document_versions_document_id'), table_name='document_versions')
    op.drop_table('document_versions')

    op.drop_column('documents', 'current_version')

    op.drop_index(op.f('ix_interview_results_decision'), table_name='interview_results')
    op.drop_index(op.f('ix_interview_results_interview_id'), table_name='interview_results')
    op.drop_index(op.f('ix_interview_results_application_id'), table_name='interview_results')
    op.drop_table('interview_results')

    op.drop_index(op.f('ix_interviews_status'), table_name='interviews')
    op.drop_index(op.f('ix_interviews_scheduled_at'), table_name='interviews')
    op.drop_index(op.f('ix_interviews_application_id'), table_name='interviews')
    op.drop_table('interviews')

    op.drop_index(op.f('ix_equivalences_status'), table_name='equivalences')
    op.drop_index(op.f('ix_equivalences_target_program_id'), table_name='equivalences')
    op.drop_index(op.f('ix_equivalences_user_id'), table_name='equivalences')
    op.drop_table('equivalences')

    op.drop_index(op.f('ix_academic_profiles_user_id'), table_name='academic_profiles')
    op.drop_table('academic_profiles')

    op.drop_index(op.f('ix_courses_semester'), table_name='courses')
    op.drop_index(op.f('ix_courses_code'), table_name='courses')
    op.drop_index(op.f('ix_courses_specialty_id'), table_name='courses')
    op.drop_index(op.f('ix_courses_program_id'), table_name='courses')
    op.drop_table('courses')

    op.drop_index(op.f('ix_specialties_code'), table_name='specialties')
    op.drop_index(op.f('ix_specialties_program_id'), table_name='specialties')
    op.drop_table('specialties')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        sa.Enum(name='vector_sync_status').drop(bind, checkfirst=True)
        sa.Enum(name='vector_sync_action').drop(bind, checkfirst=True)
        sa.Enum(name='jury_decision').drop(bind, checkfirst=True)
        sa.Enum(name='interview_status').drop(bind, checkfirst=True)
        sa.Enum(name='interview_type').drop(bind, checkfirst=True)
        sa.Enum(name='equivalence_status').drop(bind, checkfirst=True)
