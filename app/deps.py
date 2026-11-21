from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Role, User, VisitorSession
from .security import decode_access_token, hash_token

oauth2 = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------- Utilisateurs (candidat / admin) ----------
def get_optional_user(token: str | None = Depends(oauth2), db: Session = Depends(get_db)) -> User | None:
    if not token:
        return None
    uid = decode_access_token(token)
    if not uid:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Jeton d'accès invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"}
        )
    user = db.get(User, uid)
    if not user or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Compte inactif ou introuvable",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentification requise",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits insuffisants")
        return user
    return checker


require_admin = require_roles(Role.admin)
require_candidat = require_roles(Role.candidat)


# ---------- Visiteurs (sessions anonymes) ----------
def _resolve_session(db: Session, token: str | None) -> VisitorSession | None:
    if not token:
        return None
    vs = db.scalar(select(VisitorSession).where(VisitorSession.token_hash == hash_token(token)))
    if not vs:
        return None

    now = datetime.now(timezone.utc)
    created_at = _aware(vs.created_at)

    # 1. Vérification de la durée de vie absolue maximale (anti-glissement infini)
    max_lifetime = created_at + timedelta(days=settings.session_max_ttl_days)
    if now > max_lifetime:
        return None

    # 2. Vérification de la fenêtre de validité glissante courante
    if _aware(vs.expires_at) <= now:
        return None

    # Extension glissante bornée par la durée absolue maximale
    new_expires = min(now + timedelta(hours=settings.session_ttl_hours), max_lifetime)
    vs.last_seen_at = now
    vs.expires_at = new_expires
    db.commit()
    return vs


def get_optional_session(
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db)
) -> VisitorSession | None:
    return _resolve_session(db, x_session_token)


def get_session(
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db)
) -> VisitorSession:
    if not x_session_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "En-tête X-Session-Token manquant")
    vs = _resolve_session(db, x_session_token)
    if not vs:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session visiteur absente ou expirée")
    return vs
