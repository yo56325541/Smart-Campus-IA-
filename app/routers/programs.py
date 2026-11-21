import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_optional_user, require_admin
from ..models import AdmissionCondition, Institution, Program, Role, Tariff, User
from ..schemas import (ConditionIn, ConditionOut, ConditionUpdate, ProgramDetail,
                        ProgramIn, ProgramOut, ProgramUpdate, TariffIn, TariffOut,
                        TariffUpdate)

logger = logging.getLogger("smartcampus.programs")

router = APIRouter(tags=["Formations, conditions et tarifs"])


def _program(db: Session, slug: str, user: User | None = None) -> Program:
    p = db.scalar(select(Program).where(Program.slug == slug))
    is_admin = bool(user and user.role == Role.admin)
    if not p or (not p.is_active and not is_admin):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Formation introuvable")
    return p


# ================= SA-20 : formations / programmes =================

@router.get("/programs", response_model=list[ProgramOut])
def list_programs(
    institution: Institution | None = None,
    level: str | None = None,
    q: str | None = Query(default=None, description="Recherche dans nom/description"),
    include_inactive: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user)
):
    """Liste les formations avec filtrage et pagination au niveau de la base de données."""
    if include_inactive and not (user and user.role == Role.admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "include_inactive réservé à l'admin")

    stmt = select(Program)
    if not include_inactive:
        stmt = stmt.where(Program.is_active.is_(True))
    if institution:
        stmt = stmt.where(Program.institution == institution)
    if level:
        stmt = stmt.where(Program.level == level.strip().lower())
    if q:
        cleaned_q = q.strip()
        if cleaned_q:
            like = f"%{cleaned_q}%"
            stmt = stmt.where(or_(Program.name.ilike(like), Program.description.ilike(like)))

    stmt = stmt.order_by(Program.institution, Program.level, Program.name).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.get("/programs/{slug}", response_model=ProgramDetail)
def get_program(
    slug: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user)
):
    """Consulte les détails d'une formation avec ses conditions et tarifs."""
    return _program(db, slug, user)


@router.post("/programs", response_model=ProgramOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_program(
    body: ProgramIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Création d'une nouvelle formation (réservé admin)."""
    if db.scalar(select(Program).where(Program.slug == body.slug)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug déjà utilisé")

    data = body.model_dump()
    data["level"] = data["level"].lower()
    p = Program(**data)
    db.add(p)
    try:
        db.commit()
        db.refresh(p)
        logger.info(f"AUDIT: Admin '{admin.email}' a créé la formation '{p.slug}'")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug déjà utilisé")

    return p


@router.patch("/programs/{slug}", response_model=ProgramOut)
def update_program(
    slug: str,
    body: ProgramUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Mise à jour partielle d'une formation (réservé admin)."""
    p = _program(db, slug, admin)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v.lower() if k == "level" and v else v)
    db.commit()
    db.refresh(p)
    logger.info(f"AUDIT: Admin '{admin.email}' a mis à jour la formation '{p.slug}'")
    return p


@router.delete("/programs/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_program(
    slug: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Suppression logique (is_active = false) préservant l'historique."""
    p = _program(db, slug, admin)
    p.is_active = False
    db.commit()
    logger.info(f"AUDIT: Admin '{admin.email}' a désactivé la formation '{p.slug}'")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================= SA-21 : conditions d'admission =================

@router.get("/programs/{slug}/admission-conditions", response_model=list[ConditionOut])
def list_conditions(
    slug: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user)
):
    """Liste ordonnée des conditions d'admission associées à la formation."""
    p = _program(db, slug, user)
    stmt = (
        select(AdmissionCondition)
        .where(AdmissionCondition.program_id == p.id)
        .order_by(AdmissionCondition.position, AdmissionCondition.title)
    )
    return db.scalars(stmt).all()


@router.post("/programs/{slug}/admission-conditions", response_model=ConditionOut,
             status_code=status.HTTP_201_CREATED)
def add_condition(
    slug: str,
    body: ConditionIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Ajout d'une condition d'admission (réservé admin)."""
    p = _program(db, slug, admin)
    c = AdmissionCondition(program_id=p.id, **body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    logger.info(f"AUDIT: Admin '{admin.email}' a ajouté la condition '{c.id}' au programme '{slug}'")
    return c


@router.patch("/admission-conditions/{condition_id}", response_model=ConditionOut,
              dependencies=[Depends(require_admin)])
def update_condition(
    condition_id: uuid.UUID,
    body: ConditionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Mise à jour partielle d'une condition d'admission (réservé admin)."""
    c = db.get(AdmissionCondition, condition_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condition introuvable")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    logger.info(f"AUDIT: Admin '{admin.email}' a modifié la condition '{c.id}'")
    return c


@router.delete("/admission-conditions/{condition_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_condition(
    condition_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Suppression d'une condition d'admission (réservé admin)."""
    c = db.get(AdmissionCondition, condition_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condition introuvable")
    db.delete(c)
    db.commit()
    logger.info(f"AUDIT: Admin '{admin.email}' a supprimé la condition '{condition_id}'")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================= SA-21 : tarifs =================

@router.get("/programs/{slug}/tariffs", response_model=list[TariffOut])
def list_tariffs(
    slug: str,
    academic_year: str | None = None,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user)
):
    """Liste les tarifs filtrés directement en base de données."""
    p = _program(db, slug, user)
    stmt = select(Tariff).where(Tariff.program_id == p.id)
    if academic_year:
        stmt = stmt.where(Tariff.academic_year == academic_year.strip())
    stmt = stmt.order_by(Tariff.academic_year.desc())
    return db.scalars(stmt).all()


@router.post("/programs/{slug}/tariffs", response_model=TariffOut, status_code=status.HTTP_201_CREATED)
def add_tariff(
    slug: str,
    body: TariffIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Ajoute un tarif pour une année académique donnée avec vérification d'unicité."""
    p = _program(db, slug, admin)
    existing = db.scalar(
        select(Tariff).where(Tariff.program_id == p.id, Tariff.academic_year == body.academic_year)
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Tarif déjà défini pour cette année")

    t = Tariff(program_id=p.id, **body.model_dump())
    db.add(t)
    try:
        db.commit()
        db.refresh(t)
        logger.info(f"AUDIT: Admin '{admin.email}' a ajouté un tarif pour l'année '{t.academic_year}' au programme '{slug}'")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Tarif déjà défini pour cette année")

    return t


@router.patch("/tariffs/{tariff_id}", response_model=TariffOut, dependencies=[Depends(require_admin)])
def update_tariff(
    tariff_id: uuid.UUID,
    body: TariffUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Mise à jour partielle d'un tarif (réservé admin)."""
    t = db.get(Tariff, tariff_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarif introuvable")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    logger.info(f"AUDIT: Admin '{admin.email}' a modifié le tarif '{tariff_id}'")
    return t


@router.delete("/tariffs/{tariff_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_tariff(
    tariff_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Suppression d'un tarif (réservé admin)."""
    t = db.get(Tariff, tariff_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarif introuvable")
    db.delete(t)
    db.commit()
    logger.info(f"AUDIT: Admin '{admin.email}' a supprimé le tarif '{tariff_id}'")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
