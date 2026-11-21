import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user, get_optional_session
from ..models import Role, User, VisitorSession
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, needs_rehash, verify_password
from ..services import (SessionOwnedError, get_client_ip, link_session_to_user,
                         login_limiter)

logger = logging.getLogger("smartcampus.auth")

router = APIRouter(prefix="/auth", tags=["Authentification"])


def _safe_link(db: Session, vs: VisitorSession | None, user: User) -> int:
    """Rattache la session si possible ; une session déjà liée à un autre compte est ignorée silencieusement."""
    if not vs:
        return 0
    try:
        return link_session_to_user(db, vs, user)
    except SessionOwnedError:
        return 0


def _token_out(user: User, linked: int = 0) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user),
        token_type="bearer",
        user=UserOut.model_validate(user),
        linked_conversations=linked
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterIn,
    request: Request,
    db: Session = Depends(get_db),
    vs: VisitorSession | None = Depends(get_optional_session)
):
    """Inscription d'un nouveau candidat.
    Protégé par rate limiting par IP.
    Si X-Session-Token est fourni, la session et ses conversations sont rattachées au compte.
    """
    client_ip = get_client_ip(request)
    reg_key = f"register_ip:{client_ip}"
    blocked, retry_after = login_limiter.check_rate_limit(
        reg_key,
        settings.register_ip_max_attempts,
        settings.register_window_seconds
    )
    if blocked:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Trop de créations de compte depuis cette adresse IP. Veuillez réessayer plus tard.",
            headers={"Retry-After": str(retry_after)}
        )

    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email déjà utilisé")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=Role.candidat,
        is_active=True
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email déjà utilisé")

    # Enregistrer la tentative pour le rate limiting
    login_limiter.record_failure(reg_key, settings.register_window_seconds)

    linked_count = _safe_link(db, vs, user)
    return _token_out(user, linked_count)


def _authenticate(
    request: Request,
    db: Session,
    vs: VisitorSession | None,
    email: str,
    password: str
) -> TokenOut:
    """Authentifie l'utilisateur avec protection anti brute-force multi-niveaux :
    - Par couple IP + email
    - Par adresse IP globale
    - Par compte email
    Rehash automatique du mot de passe si les paramètres Argon2 ont évolué.
    """
    email_clean = email.strip().lower()
    client_ip = get_client_ip(request)

    key_pair = f"{client_ip}|{email_clean}"
    key_ip = f"login_ip:{client_ip}"
    key_account = f"login_acc:{email_clean}"

    # 1. Vérification du rate limiting
    # Couple IP + email (règle standard)
    blocked, retry_after = login_limiter.check_rate_limit(
        key_pair,
        settings.login_max_attempts,
        settings.login_window_seconds
    )
    if not blocked:
        # IP globale (anti password-spraying)
        blocked, retry_after = login_limiter.check_rate_limit(
            key_ip,
            settings.login_ip_max_attempts,
            settings.login_window_seconds
        )
    if not blocked:
        # Compte email (anti attaque distribuée contre un compte cible)
        blocked, retry_after = login_limiter.check_rate_limit(
            key_account,
            settings.login_max_attempts * 3,
            settings.login_window_seconds
        )

    if blocked:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Trop de tentatives de connexion infructueuses. Veuillez réessayer plus tard.",
            headers={"Retry-After": str(retry_after or settings.login_window_seconds)}
        )

    user = db.scalar(select(User).where(User.email == email_clean))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        # Enregistrer l'échec sur toutes les clés
        login_limiter.record_failure(key_pair, settings.login_window_seconds)
        login_limiter.record_failure(key_ip, settings.login_window_seconds)
        login_limiter.record_failure(key_account, settings.login_window_seconds)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Identifiants invalides",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Réinitialiser le compteur de tentatives en cas de succès
    login_limiter.reset(key_pair)
    login_limiter.reset(key_account)

    # Rehash sécurisé si les paramètres de l'algorithme ont été renforcés
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()

    linked_count = _safe_link(db, vs, user)
    return _token_out(user, linked_count)


@router.post("/login", response_model=TokenOut)
def login(
    body: LoginIn,
    request: Request,
    db: Session = Depends(get_db),
    vs: VisitorSession | None = Depends(get_optional_session)
):
    """Connexion avec corps JSON : {"email": "...", "password": "..."}.
    Protégé contre le brute-force avec headers Retry-After.
    """
    return _authenticate(request, db, vs, body.email, body.password)


@router.post("/token", response_model=TokenOut, include_in_schema=False)
def login_form(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    vs: VisitorSession | None = Depends(get_optional_session)
):
    """Formulaire OAuth2 standard pour le bouton Authorize de Swagger."""
    return _authenticate(request, db, vs, form.username, form.password)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """Retourne les informations du profil utilisateur authentifié."""
    return user
