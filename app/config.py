import re
from typing import List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-secret-change-me-please-use-32-bytes-min"
_DEV_ADMIN_PASSWORD = "ChangeMe123!"
_SUPPORTED_ENVIRONMENTS = frozenset({"dev", "test", "production"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Environnement : "dev", "test", ou "production".
    # En production, l'application refuse strictement les secrets par défaut.
    environment: str = "dev"

    database_url: str = "postgresql+psycopg://smartcampus:smartcampus@127.0.0.1:5433/smartcampus"
    
    # Paramètres de pool SQLAlchemy
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    jwt_secret: str = _DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    
    # Durées de vie des sessions visiteurs
    session_ttl_hours: int = 24
    session_max_ttl_days: int = 30  # Durée de vie absolue maximale (anti-glissement infini)

    admin_email: str = "admin@smartcampus.tn"
    admin_password: str = _DEV_ADMIN_PASSWORD
    cors_origins: List[str] = ["http://localhost:3000"]

    # Limitation des tentatives (anti brute-force / abus)
    login_max_attempts: int = 5
    login_window_seconds: int = 300
    login_ip_max_attempts: int = 25
    register_ip_max_attempts: int = 10
    register_window_seconds: int = 900

    # Redis pour rate limiting distribué (facultatif en dev, recommandé en prod)
    redis_url: Optional[str] = None

    # Proxies de confiance pour la résolution sécurisée des IP clientes (ex: reverse proxy nginx)
    trusted_proxies: List[str] = ["127.0.0.1", "::1"]

    # ---- Configuration LLM Local (Ollama - Modèle Gemma) ----
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:1b"
    ollama_timeout_seconds: float = 60.0
    ollama_temperature: float = 0.2
    ollama_top_p: float = 0.9
    ollama_max_tokens: int = 1024
    ollama_api_key: Optional[str] = None  # Clé API si Ollama est protégé par reverse proxy
    llm_service_api_key: Optional[str] = None  # Clé secrète d'accès à l'API LLM (/llm)
    llm_fallback_enabled: bool = True  # Repli automatique vers corpus RAG si Ollama est indisponible ou timeout

    @field_validator("environment", mode="before")
    @classmethod
    def _validate_environment(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("L'environnement doit être une chaîne de caractères.")
        clean_env = v.strip().lower()
        if clean_env not in _SUPPORTED_ENVIRONMENTS:
            raise ValueError(
                f"Environnement '{v}' non supporté. Valeurs autorisées : {', '.join(sorted(_SUPPORTED_ENVIRONMENTS))}."
            )
        return clean_env

    @model_validator(mode="after")
    def _check_production_secrets(self):
        if self.environment == "production":
            problems = []
            if self.jwt_secret == _DEV_JWT_SECRET or len(self.jwt_secret) < 32:
                problems.append("JWT_SECRET doit être défini (≥ 32 caractères, aléatoire)")
            if self.admin_password == _DEV_ADMIN_PASSWORD or len(self.admin_password) < 12:
                problems.append("ADMIN_PASSWORD doit être défini (≥ 12 caractères)")
            if not self.admin_email or "@" not in self.admin_email:
                problems.append("ADMIN_EMAIL doit être une adresse email valide")
            if not self.cors_origins:
                problems.append("CORS_ORIGINS doit contenir au moins une origine valide")
            if "*" in self.cors_origins:
                problems.append("CORS_ORIGINS ne doit pas contenir '*' en production (incompatible avec allow_credentials=True)")
            if problems:
                raise ValueError("Configuration production invalide : " + " ; ".join(problems))
        return self


settings = Settings()
