import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import ROLE_METADATA, Role, User
from ..schemas import AdminCreateUserIn, RoleInfoOut, UserActiveIn, UserOut
from ..security import hash_password

logger = logging.getLogger("smartcampus.admin")

router = APIRouter(prefix="/admin/users", tags=["Admin – utilisateurs"], dependencies=[Depends(require_admin)])
roles_router = APIRouter(prefix="/admin/roles", tags=["Admin – rôles"], dependencies=[Depends(require_admin)])


@roles_router.get("", response_model=list[RoleInfoOut])
def get_system_roles():
    """Liste exhaustive des rôles et prérogatives du système SmartCampus AI."""
    return [
        RoleInfoOut(
            code=r,
            title=meta["title"],
            description=meta["description"],
            institution=meta.get("institution"),
            permissions=meta["permissions"]
        )
        for r, meta in ROLE_METADATA.items()
    ]


@router.get("/available-roles", response_model=list[RoleInfoOut])
def get_available_roles():
    """Alias pour obtenir la liste des rôles dans le contexte de gestion des utilisateurs."""
    return get_system_roles()


@router.get("", response_model=list[UserOut])
def list_users(
    limit: int = Query(50, ge=1, le=200, description="Nombre maximal d'utilisateurs à retourner"),
    offset: int = Query(0, ge=0, description="Décalage pour pagination"),
    db: Session = Depends(get_db)
):
    """Liste les utilisateurs avec pagination au niveau base de données."""
    stmt = (
        select(User)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: AdminCreateUserIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Création administrative d'un compte (candidat ou admin) avec audit logging."""
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email déjà utilisé")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        logger.info(f"AUDIT: Admin '{admin.email}' a créé l'utilisateur '{user.email}' (rôle: {user.role.value})")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email déjà utilisé")

    return user


@router.patch("/{user_id}", response_model=UserOut)
def set_active(
    user_id: uuid.UUID,
    body: UserActiveIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Active ou désactive un compte utilisateur.
    Empêche la désactivation de son propre compte ou du dernier administrateur actif.
    """
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur introuvable")

    if not body.is_active:
        # 1. Empêcher l'auto-désactivation
        if u.id == admin.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Impossible de désactiver son propre compte")

        # 2. Protection du dernier administrateur actif
        if u.role == Role.admin and u.is_active:
            active_admins_count = db.scalar(
                select(func.count(User.id))
                .where(User.role == Role.admin, User.is_active.is_(True))
            ) or 0
            if active_admins_count <= 1:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Impossible de désactiver le dernier administrateur actif du système"
                )

    u.is_active = body.is_active
    db.commit()
    db.refresh(u)
    logger.info(f"AUDIT: Admin '{admin.email}' a modifié l'état de l'utilisateur '{u.email}' -> is_active={body.is_active}")
    return u
