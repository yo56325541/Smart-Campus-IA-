import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import Request
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import settings
from .models import Conversation, Role, User, VisitorSession
from .security import hash_password

logger = logging.getLogger("smartcampus.services")


class SessionOwnedError(Exception):
    """La session visiteur est déjà rattachée à un autre compte."""


def link_session_to_user(db: Session, vs: VisitorSession, user: User) -> int:
    """SA-29 : Rattache la session invitée et ses conversations anonymes au compte candidat.

    Le rattachement est immuable : une session déjà liée à un autre compte ne peut pas
    être réaffectée (lève SessionOwnedError). Re-lier au même compte reste idempotent.
    Garantit la concurrence via verrouillage de ligne PostgreSQL (FOR UPDATE) ou transactionnel.
    """
    if user.role != Role.candidat:
        return 0

    # Verrouillage de la session en base pour éliminer les race conditions
    locked_vs = db.scalar(
        select(VisitorSession)
        .where(VisitorSession.id == vs.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not locked_vs:
        return 0

    # Vérification stricte d'immuabilité
    if locked_vs.user_id is not None and locked_vs.user_id != user.id:
        raise SessionOwnedError("Cette session est déjà rattachée à un autre compte.")

    # Idempotence : si déjà lié au même utilisateur
    if locked_vs.user_id == user.id:
        res = db.execute(
            update(Conversation)
            .where(Conversation.session_id == locked_vs.id, Conversation.user_id.is_(None))
            .values(user_id=user.id)
        )
        db.commit()
        return res.rowcount or 0

    # Affectation atomique du propriétaire de la session
    locked_vs.user_id = user.id

    # Rattachement atomique des conversations anonymes associées
    res = db.execute(
        update(Conversation)
        .where(Conversation.session_id == locked_vs.id, Conversation.user_id.is_(None))
        .values(user_id=user.id)
    )
    db.commit()
    vs.user_id = user.id
    return res.rowcount or 0


def bootstrap_admin(db: Session) -> None:
    """Initialise le compte administrateur au démarrage de façon concurrente et sécurisée.

    Gère les démarrages simultanés de multiples workers sans lever d'exception non gérée.
    """
    email = settings.admin_email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return

    admin_user = User(
        email=email,
        password_hash=hash_password(settings.admin_password),
        full_name="Administrateur",
        role=Role.admin,
        is_active=True,
    )
    db.add(admin_user)
    try:
        db.commit()
        logger.info(f"Compte administrateur initialisé pour {email}")
    except IntegrityError:
        # Concurrence multi-workers : un autre worker vient d'insérer l'admin
        db.rollback()
        logger.debug("Compte administrateur déjà inséré par un worker concurrent.")


def get_client_ip(request: Request) -> str:
    """Détermine l'adresse IP du client en respectant les proxys de confiance."""
    client_host = request.client.host if request.client else "127.0.0.1"
    if client_host in settings.trusted_proxies:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ips = [ip.strip() for ip in forwarded_for.split(",")]
            for ip in reversed(ips):
                if ip not in settings.trusted_proxies:
                    return ip
            return ips[0]
    return client_host


# =====================================================================
# Système de limitation de débit (Rate Limiting) : In-Memory & Redis
# =====================================================================

class InMemoryRateLimiter:
    """Limiteur en mémoire avec fenêtre glissante et verrouillage par thread."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _purge(self, key: str, now: float, window_seconds: int) -> deque[float]:
        q = self._hits[key]
        while q and now - q[0] > window_seconds:
            q.popleft()
        return q

    def is_blocked(self, key: str, max_attempts: int, window_seconds: int) -> Tuple[bool, int]:
        with self._lock:
            now = time.monotonic()
            q = self._purge(key, now, window_seconds)
            if len(q) >= max_attempts:
                retry_after = int(window_seconds - (now - q[0])) + 1
                return True, max(1, retry_after)
            return False, 0

    def record_failure(self, key: str, window_seconds: int) -> None:
        with self._lock:
            now = time.monotonic()
            self._purge(key, now, window_seconds).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def clear_all(self) -> None:
        with self._lock:
            self._hits.clear()


class RedisRateLimiter:
    """Limiteur distribué adossé à Redis pour environnements multi-workers / cluster."""

    def __init__(self, redis_url: str) -> None:
        import redis
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def is_blocked(self, key: str, max_attempts: int, window_seconds: int) -> Tuple[bool, int]:
        try:
            now = time.time()
            cutoff = now - window_seconds
            pipe = self._client.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            pipe.zrange(key, 0, 0, withscores=True)
            _, count, oldest = pipe.execute()

            if count >= max_attempts:
                oldest_time = oldest[0][1] if oldest else now
                retry_after = int(window_seconds - (now - oldest_time)) + 1
                return True, max(1, retry_after)
            return False, 0
        except Exception as e:
            logger.warning(f"Erreur Redis RateLimiter: {e}, repli en mémoire")
            return in_memory_limiter.is_blocked(key, max_attempts, window_seconds)

    def record_failure(self, key: str, window_seconds: int) -> None:
        try:
            now = time.time()
            cutoff = now - window_seconds
            pipe = self._client.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zadd(key, {f"{now}_{time.perf_counter()}": now})
            pipe.expire(key, window_seconds + 5)
            pipe.execute()
        except Exception as e:
            logger.warning(f"Erreur Redis RateLimiter record: {e}")
            in_memory_limiter.record_failure(key, window_seconds)

    def reset(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception:
            in_memory_limiter.reset(key)

    def clear_all(self) -> None:
        try:
            # En test ou reset complet
            self._client.flushdb()
        except Exception:
            in_memory_limiter.clear_all()


in_memory_limiter = InMemoryRateLimiter()

if settings.redis_url:
    try:
        active_limiter = RedisRateLimiter(settings.redis_url)
        logger.info("Limiteur de débit Redis actif.")
    except Exception as e:
        logger.warning(f"Impossible d'initialiser Redis ({e}). Utilisation du limiteur en mémoire.")
        active_limiter = in_memory_limiter
else:
    if settings.environment == "production":
        logger.warning("ATTENTION: REDIS_URL n'est pas défini en production. Le limiteur en mémoire ne protège pas contre les attaques réparties sur plusieurs workers.")
    active_limiter = in_memory_limiter


class UnifiedRateLimiter:
    """Façade unifiée pour le rate limiting avec rétrocompatibilité de l'interface."""

    def is_blocked(self, key: str) -> bool:
        blocked, _ = active_limiter.is_blocked(key, settings.login_max_attempts, settings.login_window_seconds)
        return blocked

    def check_rate_limit(self, key: str, max_attempts: int, window_seconds: int) -> Tuple[bool, int]:
        return active_limiter.is_blocked(key, max_attempts, window_seconds)

    def record_failure(self, key: str, window_seconds: int | None = None) -> None:
        w = window_seconds or settings.login_window_seconds
        active_limiter.record_failure(key, w)

    def reset(self, key: str) -> None:
        active_limiter.reset(key)

    def clear_all(self) -> None:
        active_limiter.clear_all()
        in_memory_limiter.clear_all()


login_limiter = UnifiedRateLimiter()


# =====================================================================
# Cycle de vie et nettoyage des données (Data Retention)
# =====================================================================

def cleanup_expired_sessions(db: Session, retention_days: int = 7) -> int:
    """Supprime les sessions anonymes expirées non rattachées à un compte candidat.

    Les conversations associées aux sessions supprimées sont purgées si non liées,
    ou conservées selon la stratégie de rétention.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    stmt = delete(VisitorSession).where(
        VisitorSession.user_id.is_(None),
        VisitorSession.expires_at < cutoff,
    )
    res = db.execute(stmt)
    db.commit()
    return res.rowcount or 0
