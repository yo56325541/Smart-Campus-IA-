import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .models import (ApplicationStatus, DocumentType, EquivalenceStatus,
                    Institution, InterviewStatus, InterviewType,
                    JuryDecision, MessageRole, Role, SyncStatus,
                    VectorSyncAction, VectorSyncStatus)


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PatchModel(BaseModel):
    """Schéma de mise à jour partielle : un champ explicitement mis à null n'est accepté
    que s'il est nullable en base (liste `nullable_fields`). Sinon → 422 propre."""
    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_null_on_required(self):
        bad = [
            f for f in self.model_fields_set
            if getattr(self, f) is None and f not in self.nullable_fields
        ]
        if bad:
            raise ValueError(f"Valeur null interdite pour : {', '.join(sorted(bad))}")
        return self


# ---------- Auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=120)

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        return v.strip()


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORM):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    created_at: Optional[datetime] = None


class RoleInfoOut(BaseModel):
    code: Role
    title: str
    description: str
    institution: Optional[Institution] = None
    permissions: list[str]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    linked_conversations: int = 0


class AdminCreateUserIn(RegisterIn):
    role: Role = Role.candidat


class UserActiveIn(BaseModel):
    is_active: bool


# ---------- Sessions / conversations ----------
class SessionOut(BaseModel):
    session_token: str
    expires_at: datetime


class SessionInfo(ORM):
    id: uuid.UUID
    expires_at: datetime
    linked: bool


class ConversationIn(BaseModel):
    title: str = Field(default="", max_length=200)

    @field_validator("title")
    @classmethod
    def _clean_title(cls, v: str) -> str:
        return v.strip()


class ConversationOut(ORM):
    id: uuid.UUID
    title: str
    session_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    created_at: datetime


# ---------- Messages & LLM Dialogue (SA-26, SA-36, SA-38) ----------
class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def _clean_content(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Le message ne peut être vide.")
        return cleaned


class MessageOut(ORM):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut


class LinkOut(BaseModel):
    linked_conversations: int


# ---------- Catalogue ----------
class ConditionIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    required_diploma: Optional[str] = Field(default=None, max_length=120)
    min_average: Optional[Decimal] = Field(default=None, ge=0, le=20, max_digits=4, decimal_places=2)
    position: int = 0

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Le titre ne peut pas être vide ou constitué uniquement d'espaces.")
        return cleaned


class ConditionUpdate(PatchModel):
    nullable_fields: ClassVar[frozenset[str]] = frozenset({"required_diploma", "min_average"})

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    required_diploma: Optional[str] = Field(default=None, max_length=120)
    min_average: Optional[Decimal] = Field(default=None, ge=0, le=20, max_digits=4, decimal_places=2)
    position: Optional[int] = None

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Le titre ne peut pas être vide.")
            return cleaned
        return v


class ConditionOut(ORM, ConditionIn):
    id: uuid.UUID
    program_id: uuid.UUID


def validate_academic_year(v: str) -> str:
    pattern = r"^(\d{4})-(\d{4})$"
    m = re.match(pattern, v)
    if not m:
        raise ValueError("L'année universitaire doit respecter le format AAAA-AAAA (ex: 2026-2027).")
    start_year, end_year = int(m.group(1)), int(m.group(2))
    if end_year != start_year + 1:
        raise ValueError(
            f"Année universitaire invalide ({v}) : l'année de fin ({end_year}) doit suivre l'année de début ({start_year} + 1 = {start_year + 1})."
        )
    return v


class TariffIn(BaseModel):
    academic_year: str = Field(pattern=r"^\d{4}-\d{4}$")
    amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    registration_fee: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="TND", min_length=3, max_length=3)
    payment_terms: Optional[str] = None

    @field_validator("academic_year")
    @classmethod
    def _validate_academic_year(cls, v: str) -> str:
        return validate_academic_year(v)

    @field_validator("currency")
    @classmethod
    def _clean_currency(cls, v: str) -> str:
        return v.strip().upper()


class TariffUpdate(PatchModel):
    nullable_fields: ClassVar[frozenset[str]] = frozenset({"registration_fee", "payment_terms"})

    amount: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    registration_fee: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    payment_terms: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def _clean_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip().upper()
        return v


class TariffOut(ORM, TariffIn):
    id: uuid.UUID
    program_id: uuid.UUID


class ProgramIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", min_length=1, max_length=120)
    institution: Institution
    level: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    duration_years: Optional[int] = Field(default=None, ge=1, le=10)
    language: str = Field(default="fr", min_length=2, max_length=50)
    careers: str = ""
    is_active: bool = True

    @field_validator("name", "level", "language")
    @classmethod
    def _clean_non_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Ce champ ne peut être vide.")
        return cleaned


class ProgramUpdate(PatchModel):
    nullable_fields: ClassVar[frozenset[str]] = frozenset({"duration_years"})

    institution: Optional[Institution] = None
    level: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    duration_years: Optional[int] = Field(default=None, ge=1, le=10)
    language: Optional[str] = Field(default=None, min_length=2, max_length=50)
    careers: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name", "level", "language")
    @classmethod
    def _clean_non_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Ce champ ne peut être vide.")
            return cleaned
        return v


# ---------- Spécialités & Matières (SA-12) ----------
class SpecialtyIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=50)
    description: str = ""
    is_active: bool = True


class SpecialtyOut(ORM, SpecialtyIn):
    id: uuid.UUID
    program_id: uuid.UUID


class CourseIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=200)
    semester: str = Field(min_length=2, max_length=10)
    credits_ects: Decimal = Field(default=Decimal("3.0"), ge=0, max_digits=4, decimal_places=1)
    coefficient: Decimal = Field(default=Decimal("1.50"), ge=0, max_digits=4, decimal_places=2)
    hours_lectures: int = Field(default=21, ge=0)
    hours_tutorials: int = Field(default=21, ge=0)
    description: str = ""
    specialty_id: Optional[uuid.UUID] = None


class CourseOut(ORM, CourseIn):
    id: uuid.UUID
    program_id: uuid.UUID


class ProgramOut(ORM, ProgramIn):
    id: uuid.UUID


class ProgramDetail(ProgramOut):
    conditions: list[ConditionOut] = []
    tariffs: list[TariffOut] = []
    specialties: list[SpecialtyOut] = []
    courses: list[CourseOut] = []


# ---------- Candidatures (SA-13) ----------
class ApplicationIn(BaseModel):
    program_id: uuid.UUID
    academic_year: str = Field(pattern=r"^\d{4}-\d{4}$")
    notes: str = Field(default="", max_length=1000)

    @field_validator("academic_year")
    @classmethod
    def _validate_academic_year(cls, v: str) -> str:
        return validate_academic_year(v)


class ApplicationUpdate(PatchModel):
    nullable_fields: ClassVar[frozenset[str]] = frozenset({"notes"})
    notes: Optional[str] = Field(default=None, max_length=1000)


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationOut(ORM):
    id: uuid.UUID
    user_id: uuid.UUID
    program_id: uuid.UUID
    academic_year: str
    status: ApplicationStatus
    notes: str
    created_at: datetime
    updated_at: datetime


# ---------- Documents & Synchronisation (SA-14) ----------
class DocumentIn(BaseModel):
    document_type: DocumentType = DocumentType.autre
    filename: str = Field(min_length=1, max_length=255)
    file_path: str = Field(default="", max_length=500)
    mime_type: str = Field(default="application/octet-stream", max_length=100)
    file_size: int = Field(default=0, ge=0)


class DocumentOut(ORM):
    id: uuid.UUID
    application_id: Optional[uuid.UUID]
    user_id: Optional[uuid.UUID]
    document_type: DocumentType
    filename: str
    file_path: str
    mime_type: str
    file_size: int
    current_version: int = 1
    is_verified: bool
    created_at: datetime


class DocumentVersionIn(BaseModel):
    file_path: str = Field(min_length=1, max_length=500)
    file_size: int = Field(default=0, ge=0)
    change_summary: str = Field(default="Nouvelle version", max_length=255)


class DocumentVersionOut(ORM, DocumentVersionIn):
    id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    created_at: datetime


class VectorSyncTaskIn(BaseModel):
    document_id: Optional[uuid.UUID] = None
    action: VectorSyncAction = VectorSyncAction.upsert
    embedding_model: str = Field(default="text-embedding-3-small", max_length=100)
    collection_name: str = Field(default="smartcampus_documents", max_length=100)


class VectorSyncTaskOut(ORM):
    id: uuid.UUID
    document_id: Optional[uuid.UUID]
    action: VectorSyncAction
    status: VectorSyncStatus
    embedding_model: str
    collection_name: str
    chunk_count: int
    vector_dimensions: int
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]


class SyncLogOut(ORM):
    id: uuid.UUID
    entity_type: str
    status: SyncStatus
    records_synced: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]


# ---------- Profils académiques, Équivalences & Entretiens (SA-13) ----------
class AcademicProfileIn(BaseModel):
    bac_section: str = Field(default="", max_length=100)
    bac_year: Optional[int] = Field(default=None, ge=1970, le=2100)
    bac_average: Optional[Decimal] = Field(default=None, ge=0, le=20, max_digits=4, decimal_places=2)
    highest_diploma: str = Field(default="", max_length=150)
    graduation_institution: str = Field(default="", max_length=200)
    graduation_year: Optional[int] = Field(default=None, ge=1970, le=2100)
    notes: str = Field(default="", max_length=2000)


class AcademicProfileOut(ORM, AcademicProfileIn):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EquivalenceIn(BaseModel):
    target_program_id: uuid.UUID
    source_diploma: str = Field(min_length=2, max_length=200)
    source_institution: str = Field(min_length=2, max_length=200)
    source_country: str = Field(default="Tunisie", max_length=100)
    requested_level: str = Field(min_length=1, max_length=50)


class EquivalenceReviewIn(BaseModel):
    status: EquivalenceStatus
    decision_notes: str = Field(default="", max_length=1000)


class EquivalenceOut(ORM):
    id: uuid.UUID
    user_id: uuid.UUID
    target_program_id: uuid.UUID
    source_diploma: str
    source_institution: str
    source_country: str
    requested_level: str
    status: EquivalenceStatus
    decision_notes: str
    reviewed_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime


class InterviewIn(BaseModel):
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=10, le=180)
    interview_type: InterviewType = InterviewType.en_ligne
    location_or_link: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=1000)


class InterviewStatusUpdate(BaseModel):
    status: InterviewStatus


class InterviewOut(ORM, InterviewIn):
    id: uuid.UUID
    application_id: uuid.UUID
    status: InterviewStatus
    interviewer_id: Optional[uuid.UUID]
    created_at: datetime


class InterviewResultIn(BaseModel):
    technical_score: Optional[Decimal] = Field(default=None, ge=0, le=20, max_digits=4, decimal_places=2)
    motivation_score: Optional[Decimal] = Field(default=None, ge=0, le=20, max_digits=4, decimal_places=2)
    language_score: Optional[Decimal] = Field(default=None, ge=0, le=20, max_digits=4, decimal_places=2)
    decision: JuryDecision = JuryDecision.favorable
    jury_feedback: str = Field(default="", max_length=2000)


class InterviewResultOut(ORM, InterviewResultIn):
    id: uuid.UUID
    interview_id: uuid.UUID
    application_id: uuid.UUID
    overall_score: Optional[Decimal]
    evaluated_at: datetime


# =====================================================================
# LLM Local Gemma (Ollama) & Benchmark SA-32 Schemas
# =====================================================================

class LLMMessage(BaseModel):
    role: str = Field(description="Rôle de l'interlocuteur ('system', 'user', 'assistant')")
    content: str = Field(description="Contenu textuel du message")


class LLMQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000, description="Question ou message de l'utilisateur")
    conversation_id: Optional[uuid.UUID] = Field(default=None, description="Identifiant optionnel de conversation pour charger la mémoire temporaire (US-006)")
    system_prompt: Optional[str] = Field(default=None, description="Prompt système personnalisé optionnel")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Température de génération")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Échantillonnage top_p")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4096, description="Nombre maximal de jetons générés")
    inject_academic_context: bool = Field(default=True, description="Injecter automatiquement le contexte académique RAG")
    conversation_history: Optional[List[LLMMessage]] = Field(default=None, description="Historique préalable de la conversation")

    @field_validator("query")
    @classmethod
    def _clean_query(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("La requête ne peut pas être vide.")
        return cleaned


class LLMQueryResponse(BaseModel):
    response: str
    model: str
    latency_ms: float
    fallback_used: bool = False
    sources_cited: List[str] = Field(default_factory=list)
    status: str = "success"


class LLMHealthResponse(BaseModel):
    status: str
    ollama_url: str
    configured_model: str
    model_available: bool
    available_models: List[str]
    latency_ms: Optional[float] = None
    version: Optional[str] = None


class LLMModelItem(BaseModel):
    name: str
    size_bytes: Optional[int] = None
    modified_at: Optional[str] = None


class LLMEvalQuestionOut(BaseModel):
    id: str
    category: str
    language: str
    query: str
    expected_behavior: str
    evaluation_criteria: List[str]
    group_id: Optional[str] = None


class LLMEvalResultItem(BaseModel):
    id: str
    category: str
    query: str
    response: str
    expected_behavior: str
    evaluation_criteria: List[str]
    criteria_met: bool
    criteria_feedback: List[str]
    latency_ms: float
    fallback_used: bool = False


class LLMEvalSummary(BaseModel):
    total_questions: int
    evaluated_questions: int
    passed_count: int
    success_rate_percent: float
    categories: Dict[str, Dict[str, Any]]
    total_duration_seconds: float
    results: List[LLMEvalResultItem]


# =====================================================================
# Dashboard & Statistiques Direction / Responsables Académiques
# =====================================================================

class FunnelStats(BaseModel):
    visitors_sessions: int
    conversations: int
    orientations_advised: int
    preinscriptions_submitted: int
    interviews_scheduled: int
    interviews_completed: int
    inscriptions_accepted: int
    conversion_rate_preinscription_pct: float
    conversion_rate_interview_pct: float
    conversion_rate_inscription_pct: float


class ProgramDemandItem(BaseModel):
    program_id: uuid.UUID
    slug: str
    name: str
    institution: Institution
    level: str
    applications_count: int


class InstitutionStats(BaseModel):
    total_programs: int
    total_applications: int
    submitted_applications: int
    accepted_applications: int


class DashboardStatsOut(BaseModel):
    scope: str
    institution_filter: Optional[Institution] = None
    total_users: int
    total_conversations: int
    total_messages: int
    funnel: FunnelStats
    applications_by_status: dict[str, int]
    interviews_by_status: dict[str, int]
    decisions_by_type: dict[str, int]
    comparative_iit_vs_isb: dict[str, InstitutionStats]
    most_demanded_programs: list[ProgramDemandItem]
    pending_or_abandoned_dossiers_count: int


