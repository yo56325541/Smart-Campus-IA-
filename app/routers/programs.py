import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_optional_user, require_admin, require_roles
from ..models import (AdmissionCondition, Course, Institution, Program, Role,
                    Specialty, Tariff, User)
from ..schemas import (ConditionIn, ConditionOut, ConditionUpdate, CourseIn,
                        CourseOut, ProgramDetail, ProgramIn, ProgramOut,
                        ProgramUpdate, SpecialtyIn, SpecialtyOut, TariffIn,
                        TariffOut, TariffUpdate)

logger = logging.getLogger("smartcampus.programs")

router = APIRouter(tags=["Formations, conditions et tarifs"])

require_academic_manager = require_roles(
    Role.admin,
    Role.responsable_academique_iit,
    Role.responsable_academique_isb,
)


def _can_manage_institution(user: User, inst: Institution) -> bool:
    if user.role == Role.admin:
        return True
    if user.role == Role.responsable_academique_iit and inst == Institution.IIT:
        return True
    if user.role == Role.responsable_academique_isb and inst == Institution.ISB:
        return True
    return False


def check_program_permission(user: User, inst: Institution):
    if not _can_manage_institution(user, inst):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Droits insuffisants pour gérer les formations de l'institution {inst.value}"
        )


def _program(db: Session, slug: str, user: User | None = None) -> Program:
    p = db.scalar(select(Program).where(Program.slug == slug))
    is_staff = bool(user and user.role in (Role.admin, Role.direction, Role.responsable_academique_iit, Role.responsable_academique_isb))
    if not p or (not p.is_active and not is_staff):
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
    if include_inactive and not (user and user.role in (Role.admin, Role.direction, Role.responsable_academique_iit, Role.responsable_academique_isb)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "include_inactive réservé au personnel académique et administration")

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


@router.post("/programs", response_model=ProgramOut, status_code=status.HTTP_201_CREATED)
def create_program(
    body: ProgramIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_academic_manager)
):
    """Création d'une nouvelle formation (réservé admin et responsable académique de l'institution)."""
    check_program_permission(user, body.institution)
    if db.scalar(select(Program).where(Program.slug == body.slug)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug déjà utilisé")

    data = body.model_dump()
    data["level"] = data["level"].lower()
    p = Program(**data)
    db.add(p)
    try:
        db.commit()
        db.refresh(p)
        logger.info(f"AUDIT: Utilisateur '{user.email}' (rôle: {user.role.value}) a créé la formation '{p.slug}'")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug déjà utilisé")

    return p


@router.patch("/programs/{slug}", response_model=ProgramOut)
def update_program(
    slug: str,
    body: ProgramUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_academic_manager)
):
    """Mise à jour partielle d'une formation (réservé admin et responsable académique de l'institution)."""
    p = _program(db, slug, user)
    check_program_permission(user, p.institution)
    if body.institution is not None:
        check_program_permission(user, body.institution)

    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v.lower() if k == "level" and v else v)
    db.commit()
    db.refresh(p)
    logger.info(f"AUDIT: Utilisateur '{user.email}' a mis à jour la formation '{p.slug}'")
    return p


@router.delete("/programs/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_program(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_academic_manager)
):
    """Suppression logique (is_active = false) préservant l'historique."""
    p = _program(db, slug, user)
    check_program_permission(user, p.institution)
    p.is_active = False
    db.commit()
    logger.info(f"AUDIT: Utilisateur '{user.email}' a désactivé la formation '{p.slug}'")
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
    user: User = Depends(require_academic_manager)
):
    """Ajout d'une condition d'admission (réservé admin et responsable académique)."""
    p = _program(db, slug, user)
    check_program_permission(user, p.institution)
    c = AdmissionCondition(program_id=p.id, **body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    logger.info(f"AUDIT: Utilisateur '{user.email}' a ajouté la condition '{c.id}' au programme '{slug}'")
    return c


@router.patch("/admission-conditions/{condition_id}", response_model=ConditionOut)
def update_condition(
    condition_id: uuid.UUID,
    body: ConditionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_academic_manager)
):
    """Mise à jour partielle d'une condition d'admission (réservé admin et responsable académique)."""
    c = db.get(AdmissionCondition, condition_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condition introuvable")
    check_program_permission(user, c.program.institution)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    logger.info(f"AUDIT: Utilisateur '{user.email}' a modifié la condition '{c.id}'")
    return c


@router.delete("/admission-conditions/{condition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_condition(
    condition_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_academic_manager)
):
    """Suppression d'une condition d'admission (réservé admin et responsable académique)."""
    c = db.get(AdmissionCondition, condition_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condition introuvable")
    check_program_permission(user, c.program.institution)
    db.delete(c)
    db.commit()
    logger.info(f"AUDIT: Utilisateur '{user.email}' a supprimé la condition '{condition_id}'")
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
    user: User = Depends(require_academic_manager)
):
    """Ajoute un tarif pour une année académique donnée avec vérification d'unicité."""
    p = _program(db, slug, user)
    check_program_permission(user, p.institution)
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
        logger.info(f"AUDIT: Utilisateur '{user.email}' a ajouté un tarif pour l'année '{t.academic_year}' au programme '{slug}'")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Tarif déjà défini pour cette année")

    return t


@router.patch("/tariffs/{tariff_id}", response_model=TariffOut)
def update_tariff(
    tariff_id: uuid.UUID,
    body: TariffUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_academic_manager)
):
    """Mise à jour partielle d'un tarif (réservé admin et responsable académique)."""
    t = db.get(Tariff, tariff_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarif introuvable")
    check_program_permission(user, t.program.institution)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    logger.info(f"AUDIT: Utilisateur '{user.email}' a modifié le tarif '{tariff_id}'")
    return t


@router.delete("/tariffs/{tariff_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tariff(
    tariff_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_academic_manager)
):
    """Suppression d'un tarif (réservé admin et responsable académique)."""
    t = db.get(Tariff, tariff_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarif introuvable")
    check_program_permission(user, t.program.institution)
    db.delete(t)
    db.commit()
    logger.info(f"AUDIT: Utilisateur '{user.email}' a supprimé le tarif '{tariff_id}'")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================= SA-12 : Spécialités & Matières (Courses) =================

@router.get("/programs/{slug}/specialties", response_model=list[SpecialtyOut])
def list_specialties(
    slug: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user)
):
    """Liste les spécialités rattachées à la formation."""
    p = _program(db, slug, user)
    stmt = select(Specialty).where(Specialty.program_id == p.id, Specialty.is_active.is_(True)).order_by(Specialty.name)
    return db.scalars(stmt).all()


@router.post("/programs/{slug}/specialties", response_model=SpecialtyOut, status_code=status.HTTP_201_CREATED)
def add_specialty(
    slug: str,
    body: SpecialtyIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_academic_manager)
):
    """Ajoute une spécialité à une formation (réservé admin et responsable académique)."""
    p = _program(db, slug, user)
    check_program_permission(user, p.institution)
    spec = Specialty(
        program_id=p.id,
        name=body.name.strip(),
        code=body.code.strip().upper(),
        description=body.description,
        is_active=body.is_active
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    logger.info(f"AUDIT: Utilisateur '{user.email}' a créé la spécialité '{spec.code}' pour '{slug}'")
    return spec


@router.get("/programs/{slug}/courses", response_model=list[CourseOut])
def list_courses(
    slug: str,
    semester: str | None = None,
    specialty_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user)
):
    """Liste les matières enseignées d'un programme d'études avec filtres optionnels."""
    p = _program(db, slug, user)
    stmt = select(Course).where(Course.program_id == p.id)
    if semester:
        stmt = stmt.where(Course.semester == semester.strip().upper())
    if specialty_id:
        stmt = stmt.where(Course.specialty_id == specialty_id)
    stmt = stmt.order_by(Course.semester, Course.code)
    return db.scalars(stmt).all()


@router.post("/programs/{slug}/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def add_course(
    slug: str,
    body: CourseIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_academic_manager)
):
    """Ajoute une matière enseignée au programme (réservé admin et responsable académique)."""
    p = _program(db, slug, user)
    check_program_permission(user, p.institution)
    if body.specialty_id:
        spec = db.get(Specialty, body.specialty_id)
        if not spec or spec.program_id != p.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Spécialité introuvable pour ce programme")

    course = Course(
        program_id=p.id,
        specialty_id=body.specialty_id,
        code=body.code.strip().upper(),
        name=body.name.strip(),
        semester=body.semester.strip().upper(),
        credits_ects=body.credits_ects,
        coefficient=body.coefficient,
        hours_lectures=body.hours_lectures,
        hours_tutorials=body.hours_tutorials,
        description=body.description
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    logger.info(f"AUDIT: Utilisateur '{user.email}' a ajouté la matière '{course.code}' au programme '{slug}'")
    return course
