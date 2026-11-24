import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .config import settings
from .database import Base, SessionLocal, engine
from .deps import require_admin
from .models import User
from .routers import admin, applications, auth, conversations, dashboard, llm, programs, sessions
from .services import bootstrap_admin, cleanup_expired_sessions

logging.basicConfig(
    level=logging.INFO if settings.environment == "production" else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] [ReqID: %(request_id)s] %(message)s"
    if "%(request_id)s" in logging._defaultFormatter._fmt
    else "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("smartcampus.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # En dev/test, initialisation automatique des tables si non gérées par Alembic
    if settings.environment != "production":
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        bootstrap_admin(db)
    yield


app = FastAPI(
    title="SmartCampus AI – API socle",
    version="1.0.0",
    description="API socle et services de sécurité de la plateforme SmartCampus AI",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware Request-ID et Observabilité
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id

    # Journalisation structurée sans fuite d'en-têtes sensibles
    if not request.url.path.startswith(("/health", "/docs", "/openapi.json")):
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms) [ReqID: {request_id}]"
        )
    return response


# Gestionnaires d'erreurs sécurisés
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Interception fine des violations d'intégrité de la base de données.
    Évite toute exposition des requêtes SQL ou paramètres sensibles.
    """
    orig_msg = str(exc.orig).lower() if exc.orig else ""
    if "unique" in orig_msg or "duplicate key" in orig_msg or "23505" in orig_msg:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Conflit : une ressource identique existe déjà."}
        )
    if "foreign key" in orig_msg or "23503" in orig_msg:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Référence invalide vers une ressource parente inexistante."}
        )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Conflit d'intégrité des données."}
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Masquage des erreurs SQL internes inattendues afin d'éviter la divulgation d'informations."""
    logger.error(f"Erreur base de données inattendue sur {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Une erreur interne de base de données est survenue."}
    )


# Enregistrement des routeurs
for r in (auth.router, sessions.router, conversations.router, programs.router, admin.router, admin.roles_router, applications.router, dashboard.router, llm.router):
    app.include_router(r)


# =====================================================================
# Sondes de santé et d'observabilité (Liveness & Readiness)
# =====================================================================

@app.get("/health", tags=["Système"])
def health_check():
    """Vérification de l'API (rétrocompatibilité)."""
    return {"status": "ok"}


@app.get("/health/live", tags=["Système"])
def liveness_probe():
    """Sonde de vivacité Kubernetes / conteneur."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Système"])
def readiness_probe():
    """Sonde de préparation vérifiant la connectivité réelle à la base de données PostgreSQL."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Échec de la sonde de préparation (base de données inaccessible) : {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "database": "disconnected"}
        )


@app.post("/admin/cleanup-sessions", tags=["Système"], dependencies=[Depends(require_admin)])
def trigger_cleanup_sessions(retention_days: int = 7, admin_user: User = Depends(require_admin)):
    """Déclenchement manuel ou automatisé (cron) du nettoyage des sessions expirées."""
    with SessionLocal() as db:
        deleted = cleanup_expired_sessions(db, retention_days=retention_days)
    logger.info(f"AUDIT: Admin '{admin_user.email}' a déclenché le nettoyage des sessions. {deleted} sessions supprimées.")
    return {"status": "ok", "deleted_sessions": deleted}
