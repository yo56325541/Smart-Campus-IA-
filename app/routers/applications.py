"""Router candidatures (SA-13).

Endpoints :
  Candidat :
    POST   /applications                  → soumettre une candidature
    GET    /applications/me               → lister ses candidatures
    GET    /applications/{id}             → voir sa candidature
    DELETE /applications/{id}             → retirer une candidature (statut draft uniquement)

  Admin :
    GET    /admin/applications            → liste toutes les candidatures (filtres)
    GET    /admin/applications/{id}       → détail d'une candidature
    PATCH  /admin/applications/{id}/status → changer le statut / ajouter une note
    DELETE /admin/applications/{id}       → supprimer définitivement
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import Application, ApplicationStatus, Program, Role, User
from ..schemas import (ApplicationDetail, ApplicationIn, ApplicationOut,
                       ApplicationStatusIn)

logger = logging.getLogger("smartcampus.applications")

router = APIRouter(tags=["Candidatures"])


# ───────────────────────────── helpers ──────────────────────────────

def _get_application_or_404(db: Session, app_id: uuid.UUID) -> Application:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")
    return app


def _enrich(app: Application) -> ApplicationDetail:
    """Construit un ApplicationDetail à partir des relations déjà chargées."""
    d = ApplicationDetail.model_validate(app)
    if app.program:
        d.program_name = app.program.name
        d.program_slug = app.program.slug
    if app.user:
        d.applicant_email = app.user.email
        d.applicant_name = app.user.full_name
    return d


# ═══════════════════════════ Candidat ═══════════════════════════════

@router.get(
    "/applications/me",
    response_model=list[ApplicationOut],
    summary="Mes candidatures"
)
def list_my_applications(
    academic_year: str | None = None,
    app_status: ApplicationStatus | None = Query(default=None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les candidatures du candidat connecté avec filtres optionnels."""
    stmt = select(Application).where(Application.user_id == current_user.id)
    if academic_year:
        stmt = stmt.where(Application.academic_year == academic_year.strip())
    if app_status:
        stmt = stmt.where(Application.status == app_status)
    stmt = stmt.order_by(Application.created_at.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.post(
    "/applications",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Soumettre une candidature"
)
def create_application(
    body: ApplicationIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Un candidat authentifié soumet une candidature pour une formation.
    Un admin peut également soumettre une candidature pour son propre compte.
    Une seule candidature par (utilisateur, formation, année) → 409 sinon.
    """
    # Vérification que la formation existe et est active
    program = db.get(Program, body.program_id)
    if not program or not program.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Formation introuvable ou inactive")

    app = Application(
        user_id=current_user.id,
        program_id=body.program_id,
        academic_year=body.academic_year,
        notes=body.notes,
        status=ApplicationStatus.draft,
    )
    db.add(app)
    try:
        db.commit()
        db.refresh(app)
        logger.info(
            f"AUDIT: Utilisateur '{current_user.email}' a créé la candidature "
            f"'{app.id}' pour '{program.slug}' ({body.academic_year})"
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Candidature déjà existante pour cette formation et cette année académique."
        )
    return app


@router.get(
    "/applications/{application_id}",
    response_model=ApplicationOut,
    summary="Détail d'une de mes candidatures"
)
def get_my_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulte une candidature. Un candidat ne peut voir que les siennes ;
    un admin peut consulter toutes les candidatures via cet endpoint."""
    app = _get_application_or_404(db, application_id)
    if current_user.role != Role.admin and app.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès refusé")
    return app


@router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retirer une candidature"
)
def withdraw_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Un candidat peut retirer une candidature en statut **draft** uniquement.
    Un admin peut supprimer n'importe quelle candidature."""
    app = _get_application_or_404(db, application_id)

    if current_user.role != Role.admin:
        if app.user_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès refusé")
        if app.status != ApplicationStatus.draft:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Impossible de retirer une candidature en statut « {app.status.value} »."
            )

    db.delete(app)
    db.commit()
    logger.info(
        f"AUDIT: Utilisateur '{current_user.email}' a retiré la candidature '{application_id}'"
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ═══════════════════════════ Admin ══════════════════════════════════

@router.get(
    "/admin/applications",
    response_model=list[ApplicationDetail],
    summary="[Admin] Liste toutes les candidatures"
)
def admin_list_applications(
    academic_year: str | None = None,
    program_id: uuid.UUID | None = None,
    app_status: ApplicationStatus | None = Query(default=None, alias="status"),
    user_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Liste toutes les candidatures avec filtres multiples (réservé admin)."""
    stmt = select(Application)
    if academic_year:
        stmt = stmt.where(Application.academic_year == academic_year.strip())
    if program_id:
        stmt = stmt.where(Application.program_id == program_id)
    if app_status:
        stmt = stmt.where(Application.status == app_status)
    if user_id:
        stmt = stmt.where(Application.user_id == user_id)
    stmt = stmt.order_by(Application.created_at.desc()).limit(limit).offset(offset)

    apps = db.scalars(stmt).all()
    return [_enrich(a) for a in apps]


@router.get(
    "/admin/applications/{application_id}",
    response_model=ApplicationDetail,
    summary="[Admin] Détail d'une candidature"
)
def admin_get_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Vue enrichie (formation + candidat) d'une candidature (réservé admin)."""
    app = _get_application_or_404(db, application_id)
    return _enrich(app)


@router.patch(
    "/admin/applications/{application_id}/status",
    response_model=ApplicationOut,
    summary="[Admin] Modifier le statut d'une candidature"
)
def admin_update_status(
    application_id: uuid.UUID,
    body: ApplicationStatusIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Change le statut et/ou la note d'une candidature (réservé admin)."""
    app = _get_application_or_404(db, application_id)
    old_status = app.status
    app.status = body.status
    if body.notes is not None:
        app.notes = body.notes
    app.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(app)
    logger.info(
        f"AUDIT: Admin '{admin.email}' a changé le statut de la candidature "
        f"'{application_id}' : {old_status.value} → {body.status.value}"
    )
    return app


@router.delete(
    "/admin/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Admin] Supprimer définitivement une candidature"
)
def admin_delete_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Suppression physique d'une candidature (réservé admin)."""
    app = _get_application_or_404(db, application_id)
    db.delete(app)
    db.commit()
    logger.info(
        f"AUDIT: Admin '{admin.email}' a supprimé définitivement la candidature '{application_id}'"
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
