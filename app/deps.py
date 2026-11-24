import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Role, User, VisitorSession
from .security import decode_access_token, hash_token

oauth2 = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)
session_api_key = APIKeyHeader(name="X-Session-Token", auto_error=False)
llm_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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
require_direction = require_roles(Role.admin, Role.direction)
require_responsable_iit = require_roles(Role.admin, Role.responsable_academique_iit)
require_responsable_isb = require_roles(Role.admin, Role.responsable_academique_isb)
require_responsable_academique = require_roles(
    Role.admin,
    Role.responsable_academique_iit,
    Role.responsable_academique_isb,
)
require_responsable_entretien = require_roles(Role.admin, Role.responsable_entretien)
require_staff = require_roles(
    Role.admin,
    Role.direction,
    Role.responsable_academique_iit,
    Role.responsable_academique_isb,
    Role.responsable_entretien,
)


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
    x_session_token: str | None = Header(default=None, alias="X-Session-Token", description="Jeton de session obtenu via POST /sessions"),
    auth_header: str | None = Depends(session_api_key),
    db: Session = Depends(get_db)
) -> VisitorSession | None:
    token = x_session_token or auth_header
    if not token:
        return None
    clean = token.strip().strip('"').strip("'")
    if not clean or clean.lower() == "x-session-token":
        return None
    return _resolve_session(db, clean)


def get_session(
    x_session_token: str | None = Header(default=None, alias="X-Session-Token", description="Jeton de session obtenu via POST /sessions"),
    auth_header: str | None = Depends(session_api_key),
    db: Session = Depends(get_db)
) -> VisitorSession:
    token = x_session_token or auth_header
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "En-tête X-Session-Token manquant")
    clean = token.strip().strip('"').strip("'")
    if not clean or clean.lower() == "x-session-token":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session visiteur absente ou invalide")
    vs = _resolve_session(db, clean)
    if not vs:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session visiteur absente ou expirée")
    return vs


# ---------- Protection de l'API LLM (Clé d'accès & Sécurité) ----------
def verify_llm_access(
    x_api_key: str | None = Header(default=None, alias="X-API-Key", description="Clé secrète d'accès au service LLM"),
    auth_header: str | None = Depends(oauth2),
    session_header: str | None = Depends(session_api_key),
    db: Session = Depends(get_db)
) -> bool:
    """Protège les endpoints LLM.
    Si LLM_SERVICE_API_KEY est défini dans la configuration :
      - Valide l'en-tête 'X-API-Key' en temps constant (secrets.compare_digest)
      - OU valide un jeton Bearer (clé secrète ou utilisateur JWT actif)
      - OU valide une session visiteur active
    Empêche toute fuite d'informations ou utilisation abusive.
    """
    configured_key = settings.llm_service_api_key
    if not configured_key or not configured_key.strip():
        # Pas de clé d'accès globale configurée : l'accès reste autorisé (ex: mode local dev)
        return True

    # 1. Validation de l'en-tête X-API-Key
    if x_api_key and secrets.compare_digest(x_api_key.strip(), configured_key.strip()):
        return True

    # 2. Validation de l'en-tête Bearer
    if auth_header:
        # Correspondance directe avec la clé de service
        if secrets.compare_digest(auth_header.strip(), configured_key.strip()):
            return True
        # Ou jeton JWT utilisateur valide
        uid = decode_access_token(auth_header.strip())
        if uid:
            user = db.get(User, uid)
            if user and user.is_active:
                return True

    # 3. Validation de session visiteur
    if session_header:
        vs = _resolve_session(db, session_header.strip())
        if vs:
            return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Accès refusé au service LLM : clé d'API (X-API-Key) ou authentification valide requise.",
        headers={"WWW-Authenticate": "ApiKey"}
    )

