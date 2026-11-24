"""API pour la gestion des candidatures (SA-13) et des documents / synchronisation (SA-14)."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_admin, require_candidat, require_roles
from ..models import (
    AcademicProfile,
    Application,
    ApplicationStatus,
    Document,
    DocumentType,
    DocumentVersion,
    EquivalenceRequest,
    EquivalenceStatus,
    Institution,
    InterviewAppointment,
    InterviewResult,
    InterviewStatus,
    Program,
    Role,
    SyncLog,
    User,
    VectorSyncAction,
    VectorSyncStatus,
    VectorSyncTask,
)
from ..schemas import (
    AcademicProfileIn,
    AcademicProfileOut,
    ApplicationIn,
    ApplicationOut,
    ApplicationStatusUpdate,
    ApplicationUpdate,
    DocumentIn,
    DocumentOut,
    DocumentVersionIn,
    DocumentVersionOut,
    EquivalenceIn,
    EquivalenceOut,
    EquivalenceReviewIn,
    InterviewIn,
    InterviewOut,
    InterviewResultIn,
    InterviewResultOut,
    InterviewStatusUpdate,
    SyncLogOut,
    VectorSyncTaskIn,
    VectorSyncTaskOut,
)
from db.seed import seed_database

logger = logging.getLogger("smartcampus.applications")

router = APIRouter(tags=["Candidatures & Documents"])


def can_access_application(user: User, app_obj: Application) -> bool:
    """Vérifie si l'utilisateur a le droit de consulter cette candidature."""
    if user.role in (Role.admin, Role.direction, Role.responsable_entretien):
        return True
    if user.role == Role.responsable_academique_iit:
        return app_obj.program.institution == Institution.IIT
    if user.role == Role.responsable_academique_isb:
        return app_obj.program.institution == Institution.ISB
    return app_obj.user_id == user.id


def can_manage_application_status(user: User, app_obj: Application) -> bool:
    """Vérifie si l'utilisateur a le droit de modifier le statut de cette candidature."""
    if user.role in (Role.admin, Role.direction):
        return True
    if user.role == Role.responsable_academique_iit and app_obj.program.institution == Institution.IIT:
        return True
    if user.role == Role.responsable_academique_isb and app_obj.program.institution == Institution.ISB:
        return True
    return False


def can_review_equivalence(user: User, eq: EquivalenceRequest) -> bool:
    """Vérifie si l'utilisateur peut statuer sur l'équivalence."""
    if user.role == Role.admin:
        return True
    if user.role == Role.responsable_academique_iit and eq.target_program.institution == Institution.IIT:
        return True
    if user.role == Role.responsable_academique_isb and eq.target_program.institution == Institution.ISB:
        return True
    return False


# =====================================================================
# SA-13 : Candidatures
# =====================================================================

@router.post("/applications", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(
    body: ApplicationIn,
    user: User = Depends(require_candidat),
    db: Session = Depends(get_db)
):
    """Création d'un dossier de candidature par un candidat connecté."""
    # Vérifier que le programme visé existe et est actif
    program = db.get(Program, body.program_id)
    if not program or not program.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Formation inexistante ou inactive")

    # Vérifier si une candidature existe déjà pour ce candidat / programme / année
    existing = db.scalar(
        select(Application).where(
            Application.user_id == user.id,
            Application.program_id == body.program_id,
            Application.academic_year == body.academic_year
        )
    )
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Une candidature existe déjà pour cette formation et l'année {body.academic_year}"
        )

    app_obj = Application(
        user_id=user.id,
        program_id=body.program_id,
        academic_year=body.academic_year,
        status=ApplicationStatus.draft,
        notes=body.notes,
    )
    db.add(app_obj)
    try:
        db.commit()
        db.refresh(app_obj)
        logger.info(f"AUDIT: Candidat '{user.email}' a créé la candidature '{app_obj.id}' pour le programme '{program.slug}'")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Candidature déjà existante pour ce programme et cette année")

    return app_obj


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(
    program_id: Optional[uuid.UUID] = None,
    academic_year: Optional[str] = None,
    status_filter: Optional[ApplicationStatus] = Query(default=None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Liste les candidatures avec filtrage automatique selon les prérogatives du rôle :
    - Candidat : voit uniquement ses propres candidatures
    - Responsable IIT : candidatures orientées vers l'IIT
    - Responsable ISB : candidatures orientées vers l'ISB
    - Admin, Direction, Responsable Entretien : toutes les candidatures avec filtres
    """
    stmt = select(Application).join(Application.program)
    if user.role == Role.candidat:
        stmt = stmt.where(Application.user_id == user.id)
    elif user.role == Role.responsable_academique_iit:
        stmt = stmt.where(Program.institution == Institution.IIT)
        if program_id:
            stmt = stmt.where(Application.program_id == program_id)
    elif user.role == Role.responsable_academique_isb:
        stmt = stmt.where(Program.institution == Institution.ISB)
        if program_id:
            stmt = stmt.where(Application.program_id == program_id)
    else:
        if program_id:
            stmt = stmt.where(Application.program_id == program_id)

    if academic_year:
        stmt = stmt.where(Application.academic_year == academic_year.strip())
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)

    stmt = stmt.order_by(Application.created_at.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.get("/applications/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les détails d'une candidature spécifique avec contrôle des droits."""
    app_obj = db.get(Application, application_id)
    if not app_obj or not can_access_application(user, app_obj):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    return app_obj


@router.patch("/applications/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: uuid.UUID,
    body: ApplicationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mise à jour des notes ou informations d'une candidature."""
    app_obj = db.get(Application, application_id)
    if not app_obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    if not can_access_application(user, app_obj):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    if body.notes is not None:
        app_obj.notes = body.notes

    app_obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(app_obj)
    return app_obj


@router.patch("/applications/{application_id}/status", response_model=ApplicationOut)
def update_application_status(
    application_id: uuid.UUID,
    body: ApplicationStatusUpdate,
    user: User = Depends(require_roles(Role.admin, Role.direction, Role.responsable_academique_iit, Role.responsable_academique_isb)),
    db: Session = Depends(get_db)
):
    """Mise à jour du statut d'une candidature (admin, direction ou responsable académique de l'établissement)."""
    app_obj = db.get(Application, application_id)
    if not app_obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    if not can_manage_application_status(user, app_obj):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits insuffisants pour statuer sur cette candidature")

    old_status = app_obj.status.value
    app_obj.status = body.status
    app_obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(app_obj)
    logger.info(f"AUDIT: Utilisateur '{user.email}' ({user.role.value}) a changé le statut de la candidature '{application_id}' : {old_status} -> {body.status.value}")
    return app_obj


# =====================================================================
# SA-14 : Documents et Synchronisation
# =====================================================================

@router.post("/applications/{application_id}/documents", response_model=DocumentOut,
             status_code=status.HTTP_201_CREATED)
def add_application_document(
    application_id: uuid.UUID,
    body: DocumentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dépôt ou association d'une pièce jointe au dossier de candidature."""
    app_obj = db.get(Application, application_id)
    if not app_obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    if not can_access_application(user, app_obj):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    doc = Document(
        application_id=app_obj.id,
        user_id=app_obj.user_id,
        document_type=body.document_type,
        filename=body.filename.strip(),
        file_path=body.file_path.strip(),
        mime_type=body.mime_type.strip(),
        file_size=body.file_size,
        is_verified=False,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    logger.info(f"Document '{doc.filename}' ({doc.document_type.value}) ajouté à la candidature '{application_id}'")
    return doc


@router.get("/applications/{application_id}/documents", response_model=list[DocumentOut])
def list_application_documents(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Liste les documents associés à un dossier de candidature."""
    app_obj = db.get(Application, application_id)
    if not app_obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    if not can_access_application(user, app_obj):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    stmt = select(Document).where(Document.application_id == app_obj.id).order_by(Document.created_at.asc())
    return db.scalars(stmt).all()


@router.patch("/documents/{document_id}/verify", response_model=DocumentOut)
def verify_document(
    document_id: uuid.UUID,
    is_verified: bool = Query(True),
    user: User = Depends(require_roles(Role.admin, Role.responsable_academique_iit, Role.responsable_academique_isb)),
    db: Session = Depends(get_db)
):
    """Validation de conformité d'un document justificatif (admin ou responsable académique)."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")

    if doc.application and not can_manage_application_status(user, doc.application):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits insuffisants pour vérifier ce document")

    doc.is_verified = is_verified
    db.commit()
    db.refresh(doc)
    logger.info(f"AUDIT: Utilisateur '{user.email}' a marqué le document '{doc.id}' is_verified={is_verified}")
    return doc


@router.get("/admin/sync-logs", response_model=list[SyncLogOut], dependencies=[Depends(require_admin)])
def list_sync_logs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Consultation du journal de synchronisation (audit RAG, catalogue, données)."""
    stmt = select(SyncLog).order_by(SyncLog.started_at.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.post("/admin/sync-catalog", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])
def trigger_catalog_sync(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Déclenche la synchronisation et le peuplement du catalogue académique."""
    result = seed_database(db)
    logger.info(f"AUDIT: Admin '{admin.email}' a déclenché une synchronisation du catalogue")
    return {"message": "Synchronisation du catalogue terminée", "details": result}


# =====================================================================
# SA-14 : Versions de documents et Traitements vectoriels
# =====================================================================

@router.post("/documents/{document_id}/versions", response_model=DocumentVersionOut, status_code=status.HTTP_201_CREATED)
def add_document_version(
    document_id: uuid.UUID,
    body: DocumentVersionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ajoute une nouvelle révision/version à un document existant (SA-14)."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")

    if user.role != Role.admin and doc.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")

    doc.current_version += 1
    doc.file_path = body.file_path.strip()
    doc.file_size = body.file_size
    doc.is_verified = False  # Nouvelle version nécessite une nouvelle vérification

    version_obj = DocumentVersion(
        document_id=doc.id,
        version_number=doc.current_version,
        file_path=body.file_path.strip(),
        file_size=body.file_size,
        change_summary=body.change_summary.strip()
    )
    db.add(version_obj)
    db.commit()
    db.refresh(version_obj)
    logger.info(f"Version {version_obj.version_number} ajoutée au document '{document_id}'")
    return version_obj


@router.get("/documents/{document_id}/versions", response_model=list[DocumentVersionOut])
def list_document_versions(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Consulte l'historique des différentes versions d'un document (SA-14)."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")

    if user.role != Role.admin and doc.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")

    stmt = select(DocumentVersion).where(DocumentVersion.document_id == doc.id).order_by(DocumentVersion.version_number.desc())
    return db.scalars(stmt).all()


@router.post("/documents/{document_id}/vector-sync", response_model=VectorSyncTaskOut, status_code=status.HTTP_202_ACCEPTED,
             dependencies=[Depends(require_admin)])
def schedule_vector_sync(
    document_id: uuid.UUID,
    body: VectorSyncTaskIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Déclenche et enregistre le suivi du traitement automatique de vectorisation (RAG / SA-14)."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")

    task = VectorSyncTask(
        document_id=doc.id,
        action=body.action,
        status=VectorSyncStatus.completed,  # Simulation du traitement d'indexation
        embedding_model=body.embedding_model,
        collection_name=body.collection_name,
        chunk_count=max(1, doc.file_size // 1000) if doc.file_size else 1,
        vector_dimensions=1536,
        processed_at=datetime.now(timezone.utc)
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info(f"AUDIT: Traitement vectoriel enregistré pour le document '{document_id}' : {task.chunk_count} chunks indexés")
    return task


@router.get("/admin/vector-sync-tasks", response_model=list[VectorSyncTaskOut], dependencies=[Depends(require_admin)])
def list_vector_sync_tasks(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Liste les traitements automatiques de mise à jour de la base vectorielle."""
    stmt = select(VectorSyncTask).order_by(VectorSyncTask.created_at.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()


# =====================================================================
# SA-13 : Profil académique, Équivalences & Entretiens
# =====================================================================

@router.get("/users/me/academic-profile", response_model=AcademicProfileOut)
def get_my_academic_profile(
    user: User = Depends(require_candidat),
    db: Session = Depends(get_db)
):
    """Consulte le profil académique du candidat connecté (SA-13)."""
    prof = db.scalar(select(AcademicProfile).where(AcademicProfile.user_id == user.id))
    if not prof:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil académique non encore renseigné")
    return prof


@router.post("/users/me/academic-profile", response_model=AcademicProfileOut)
def upsert_my_academic_profile(
    body: AcademicProfileIn,
    user: User = Depends(require_candidat),
    db: Session = Depends(get_db)
):
    """Crée ou met à jour le profil académique du candidat connecté (SA-13)."""
    prof = db.scalar(select(AcademicProfile).where(AcademicProfile.user_id == user.id))
    if not prof:
        prof = AcademicProfile(user_id=user.id, **body.model_dump())
        db.add(prof)
    else:
        for k, v in body.model_dump().items():
            setattr(prof, k, v)
        prof.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prof)
    return prof


@router.post("/equivalences", response_model=EquivalenceOut, status_code=status.HTTP_201_CREATED)
def create_equivalence_request(
    body: EquivalenceIn,
    user: User = Depends(require_candidat),
    db: Session = Depends(get_db)
):
    """Dépôt d'une demande d'équivalence de diplôme par un candidat (SA-13)."""
    prog = db.get(Program, body.target_program_id)
    if not prog or not prog.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programme cible introuvable ou inactif")

    eq = EquivalenceRequest(
        user_id=user.id,
        target_program_id=body.target_program_id,
        source_diploma=body.source_diploma.strip(),
        source_institution=body.source_institution.strip(),
        source_country=body.source_country.strip(),
        requested_level=body.requested_level.strip(),
        status=EquivalenceStatus.pending
    )
    db.add(eq)
    db.commit()
    db.refresh(eq)
    logger.info(f"Demande d'équivalence '{eq.id}' créée par le candidat '{user.email}'")
    return eq


@router.get("/equivalences", response_model=list[EquivalenceOut])
def list_equivalences(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Liste les demandes d'équivalences filtrées selon le rôle."""
    stmt = select(EquivalenceRequest).join(EquivalenceRequest.target_program)
    if user.role == Role.candidat:
        stmt = stmt.where(EquivalenceRequest.user_id == user.id)
    elif user.role == Role.responsable_academique_iit:
        stmt = stmt.where(Program.institution == Institution.IIT)
    elif user.role == Role.responsable_academique_isb:
        stmt = stmt.where(Program.institution == Institution.ISB)

    stmt = stmt.order_by(EquivalenceRequest.created_at.desc())
    return db.scalars(stmt).all()


@router.patch("/equivalences/{equivalence_id}/review", response_model=EquivalenceOut)
def review_equivalence(
    equivalence_id: uuid.UUID,
    body: EquivalenceReviewIn,
    reviewer: User = Depends(require_roles(Role.admin, Role.responsable_academique_iit, Role.responsable_academique_isb)),
    db: Session = Depends(get_db)
):
    """Traitement et validation d'une demande d'équivalence par le responsable académique ou l'admin (SA-13)."""
    eq = db.get(EquivalenceRequest, equivalence_id)
    if not eq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande d'équivalence introuvable")

    if not can_review_equivalence(reviewer, eq):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits insuffisants pour valider cette équivalence")

    eq.status = body.status
    eq.decision_notes = body.decision_notes.strip()
    eq.reviewed_by = reviewer.id
    eq.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(eq)
    logger.info(f"AUDIT: Utilisateur '{reviewer.email}' a statué sur l'équivalence '{equivalence_id}' -> {body.status.value}")
    return eq


@router.post("/applications/{application_id}/interview", response_model=InterviewOut, status_code=status.HTTP_201_CREATED)
def schedule_interview(
    application_id: uuid.UUID,
    body: InterviewIn,
    interviewer: User = Depends(require_roles(Role.admin, Role.responsable_entretien)),
    db: Session = Depends(get_db)
):
    """Programmation d'un rendez-vous d'entretien pour une candidature (responsable entretien ou admin)."""
    app_obj = db.get(Application, application_id)
    if not app_obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    existing = db.scalar(select(InterviewAppointment).where(InterviewAppointment.application_id == app_obj.id))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un entretien est déjà programmé pour cette candidature")

    interview = InterviewAppointment(
        application_id=app_obj.id,
        scheduled_at=body.scheduled_at,
        duration_minutes=body.duration_minutes,
        interview_type=body.interview_type,
        location_or_link=body.location_or_link.strip(),
        status=InterviewStatus.programme,
        interviewer_id=interviewer.id,
        notes=body.notes
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    logger.info(f"AUDIT: Entretien programmé pour la candidature '{application_id}' par '{interviewer.email}' le {body.scheduled_at}")
    return interview


@router.get("/applications/{application_id}/interview", response_model=InterviewOut)
def get_interview(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Consulte le rendez-vous d'entretien d'une candidature."""
    app_obj = db.get(Application, application_id)
    if not app_obj or not can_access_application(user, app_obj):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    interview = db.scalar(select(InterviewAppointment).where(InterviewAppointment.application_id == app_obj.id))
    if not interview:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun entretien programmé")
    return interview


@router.post("/applications/{application_id}/interview/result", response_model=InterviewResultOut,
             status_code=status.HTTP_201_CREATED)
def record_interview_result(
    application_id: uuid.UUID,
    body: InterviewResultIn,
    interviewer: User = Depends(require_roles(Role.admin, Role.responsable_entretien)),
    db: Session = Depends(get_db)
):
    """Enregistre l'évaluation et les résultats du jury après entretien (responsable entretien ou admin)."""
    app_obj = db.get(Application, application_id)
    if not app_obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    interview = db.scalar(select(InterviewAppointment).where(InterviewAppointment.application_id == app_obj.id))
    if not interview:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aucun entretien préalable trouvé pour cette candidature")

    existing_res = db.scalar(select(InterviewResult).where(InterviewResult.application_id == app_obj.id))
    if existing_res:
        raise HTTPException(status.HTTP_409_CONFLICT, "Les résultats de cet entretien sont déjà saisis")

    # Calcul de la moyenne générale
    scores = [s for s in [body.technical_score, body.motivation_score, body.language_score] if s is not None]
    overall = sum(scores) / len(scores) if scores else None

    res = InterviewResult(
        interview_id=interview.id,
        application_id=app_obj.id,
        technical_score=body.technical_score,
        motivation_score=body.motivation_score,
        language_score=body.language_score,
        overall_score=overall,
        decision=body.decision,
        jury_feedback=body.jury_feedback.strip()
    )
    interview.status = InterviewStatus.effectue
    db.add(res)
    db.commit()
    db.refresh(res)
    logger.info(f"AUDIT: Résultats d'entretien enregistrés par '{interviewer.email}' pour '{application_id}' (décision={body.decision.value})")
    return res


@router.get("/applications/{application_id}/interview/result", response_model=InterviewResultOut)
def get_interview_result(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Consulte les résultats et l'avis du jury pour une candidature."""
    app_obj = db.get(Application, application_id)
    if not app_obj or not can_access_application(user, app_obj):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")

    res = db.scalar(select(InterviewResult).where(InterviewResult.application_id == app_obj.id))
    if not res:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Résultats d'entretien non disponibles")
    return res
