"""Modèles SQLAlchemy pour SmartCampus AI.
Aligné avec PostgreSQL (enums, numeric, foreign keys ON DELETE, index).
Couvre l'intégralité du modèle métier (Membre 2 : SA-12, SA-13, SA-14, SA-17, SA-18, SA-22, SA-26).
"""
import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (Boolean, DateTime, Enum, ForeignKey, Integer, Numeric,
                        String, Text, UniqueConstraint, Uuid, Index)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Institution(str, enum.Enum):
    IIT = "IIT"
    ISB = "ISB"


class Role(str, enum.Enum):
    admin = "admin"
    candidat = "candidat"
    responsable_academique_iit = "responsable_academique_iit"
    responsable_academique_isb = "responsable_academique_isb"
    responsable_entretien = "responsable_entretien"
    direction = "direction"


ROLE_METADATA: dict[Role, dict] = {
    Role.responsable_academique_iit: {
        "title": "Responsable académique IIT",
        "description": "Supervise les informations et recommandations concernant les formations proposées par l'IIT.",
        "institution": Institution.IIT,
        "permissions": [
            "Consulter les candidats orientés vers l'IIT",
            "Accéder à leur profil et aux recommandations générées",
            "Vérifier la cohérence de l'orientation proposée",
            "Consulter les résultats du QCM",
            "Confirmer ou ajuster une recommandation académique",
            "Gérer les informations relatives aux formations IIT utilisées par le système",
            "Consulter les statistiques d'intérêt et d'orientation vers les différents parcours",
        ],
    },
    Role.responsable_academique_isb: {
        "title": "Responsable académique ISB",
        "description": "Supervise les informations et recommandations concernant les formations proposées par l'ISB.",
        "institution": Institution.ISB,
        "permissions": [
            "Consulter les candidats orientés vers l'ISB",
            "Accéder à leur profil et aux recommandations générées",
            "Vérifier la cohérence de l'orientation proposée",
            "Consulter les résultats du QCM",
            "Confirmer ou ajuster une recommandation académique",
            "Gérer les informations relatives aux formations ISB utilisées par le système",
            "Consulter les statistiques d'intérêt et d'orientation vers les différents parcours",
        ],
    },
    Role.responsable_entretien: {
        "title": "Responsable entretien",
        "description": "Organise et réalise les entretiens des candidats préinscrits.",
        "institution": None,
        "permissions": [
            "Consulter les candidats prêts pour un entretien",
            "Accéder au résumé de leur parcours conversationnel, à leur profil et à la formation recommandée",
            "Consulter le QCM généré automatiquement et les réponses du candidat",
            "Disposer d'une synthèse des points à approfondir pendant l'entretien",
            "Définir ou valider un rendez-vous",
            "Envoyer une invitation",
            "Saisir le résultat et les observations de l'entretien",
            "Demander un complément d'information ou transmettre le dossier à l'étape suivante",
        ],
    },
    Role.direction: {
        "title": "Direction",
        "description": "Supervise globalement le processus d'orientation, de préinscription et de conversion des candidats.",
        "institution": None,
        "permissions": [
            "Consulter un tableau de bord global",
            "Suivre le nombre de conversations, orientations, préinscriptions, entretiens et inscriptions",
            "Analyser les formations les plus demandées",
            "Comparer les orientations IIT/ISB",
            "Suivre les taux de transformation visiteur -> préinscription -> entretien -> inscription",
            "Consulter les indicateurs de performance du système agentique",
            "Identifier les dossiers en attente ou abandonnés",
            "Accéder à des statistiques et rapports d'aide à la décision",
        ],
    },
    Role.admin: {
        "title": "Administrateur",
        "description": "Supervise et administre l'ensemble du système et des utilisateurs.",
        "institution": None,
        "permissions": ["Toutes les permissions administratives et de gestion"],
    },
    Role.candidat: {
        "title": "Candidat",
        "description": "Candidat ou futur étudiant explorant les formations et postulant.",
        "institution": None,
        "permissions": [
            "Explorer les formations",
            "Dialoguer avec le conseiller IA",
            "Déposer et suivre sa candidature",
        ],
    },
}


class ApplicationStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    accepted = "accepted"
    rejected = "rejected"


class DocumentType(str, enum.Enum):
    diplome = "diplome"
    releve_notes = "releve_notes"
    cin = "cin"
    cv = "cv"
    autre = "autre"


class SyncStatus(str, enum.Enum):
    in_progress = "in_progress"
    success = "success"
    failed = "failed"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class EquivalenceStatus(str, enum.Enum):
    pending = "pending"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"


class InterviewType(str, enum.Enum):
    en_ligne = "en_ligne"
    presentiel = "presentiel"


class InterviewStatus(str, enum.Enum):
    programme = "programme"
    confirme = "confirme"
    effectue = "effectue"
    annule = "annule"


class JuryDecision(str, enum.Enum):
    favorable = "favorable"
    defavorable = "defavorable"
    liste_attente = "liste_attente"


class VectorSyncAction(str, enum.Enum):
    upsert = "upsert"
    delete = "delete"


class VectorSyncStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


# =====================================================================
# SA-13 : Utilisateurs & Profils
# =====================================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=Role.candidat
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    applications: Mapped[list["Application"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    academic_profile: Mapped["AcademicProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    equivalences: Mapped[list["EquivalenceRequest"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="EquivalenceRequest.user_id"
    )


# =====================================================================
# SA-12 : Catalogue Académique (Formations, Spécialités, Matières, Tarifs)
# =====================================================================

class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    institution: Mapped[Institution] = mapped_column(
        Enum(Institution, name="institution", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        index=True
    )
    level: Mapped[str] = mapped_column(String(50), index=True)  # licence | prepa | ingenierie | master
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Text] = mapped_column(Text, default="")
    duration_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String(50), default="fr")
    careers: Mapped[Text] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    conditions: Mapped[list["AdmissionCondition"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", order_by="AdmissionCondition.position"
    )
    tariffs: Mapped[list["Tariff"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", order_by="Tariff.academic_year"
    )
    applications: Mapped[list["Application"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    specialties: Mapped[list["Specialty"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", order_by="Specialty.name"
    )
    courses: Mapped[list["Course"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", order_by="Course.semester, Course.code"
    )


class Specialty(Base):
    """Spécialités d'une formation (ex: Génie Logiciel, Cybersécurité, Data Science)."""
    __tablename__ = "specialties"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    code: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    program: Mapped[Program] = relationship(back_populates="specialties")
    courses: Mapped[list["Course"]] = relationship(back_populates="specialty")


class Course(Base):
    """Matières enseignées d'un programme d'études (syllabus, crédits ECTS, volume horaire)."""
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), index=True)
    specialty_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("specialties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(200))
    semester: Mapped[str] = mapped_column(String(10), index=True)  # S1, S2, S3, S4, S5, S6
    credits_ects: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("3.0"))
    coefficient: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.50"))
    hours_lectures: Mapped[int] = mapped_column(Integer, default=21)
    hours_tutorials: Mapped[int] = mapped_column(Integer, default=21)
    description: Mapped[str] = mapped_column(Text, default="")

    program: Mapped[Program] = relationship(back_populates="courses")
    specialty: Mapped[Specialty | None] = relationship(back_populates="courses")


class AdmissionCondition(Base):
    __tablename__ = "admission_conditions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    required_diploma: Mapped[str | None] = mapped_column(String(120), nullable=True)
    min_average: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    program: Mapped[Program] = relationship(back_populates="conditions")


class Tariff(Base):
    __tablename__ = "tariffs"
    __table_args__ = (
        UniqueConstraint("program_id", "academic_year", name="uq_tariffs_program_academic_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), index=True)
    academic_year: Mapped[str] = mapped_column(String(9))  # e.g. "2026-2027"
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    registration_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)

    program: Mapped[Program] = relationship(back_populates="tariffs")


# =====================================================================
# SA-13 & SA-26 : Sessions Visiteurs & Conversations
# =====================================================================

class VisitorSession(Base):
    """Session anonyme visiteur. Seul le hash SHA-256 du jeton est conservé en base."""
    __tablename__ = "visitor_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Conversation(Base):
    """Conversations de SmartCampus AI."""
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visitor_sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    session: Mapped[VisitorSession] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    """Messages échangés au sein d'une conversation (mémoire conversationnelle du LLM, SA-26)."""
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=MessageRole.user
    )
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


# =====================================================================
# SA-13 : Candidatures, Profils Académiques, Équivalences & Entretiens
# =====================================================================

class AcademicProfile(Base):
    """Profil académique détaillé du candidat (cursus antérieur, baccalauréat, moyenne)."""
    __tablename__ = "academic_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    bac_section: Mapped[str] = mapped_column(String(100), default="")
    bac_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bac_average: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    highest_diploma: Mapped[str] = mapped_column(String(150), default="")
    graduation_institution: Mapped[str] = mapped_column(String(200), default="")
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="academic_profile")


class EquivalenceRequest(Base):
    """Demandes d'équivalence de diplômes ou de crédits pour admission en année supérieure."""
    __tablename__ = "equivalences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), index=True)
    source_diploma: Mapped[str] = mapped_column(String(200))
    source_institution: Mapped[str] = mapped_column(String(200))
    source_country: Mapped[str] = mapped_column(String(100), default="Tunisie")
    requested_level: Mapped[str] = mapped_column(String(50))
    status: Mapped[EquivalenceStatus] = mapped_column(
        Enum(EquivalenceStatus, name="equivalence_status", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=EquivalenceStatus.pending,
        index=True
    )
    decision_notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="equivalences")
    target_program: Mapped[Program] = relationship()
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])


class Application(Base):
    """Dossier de candidature d'un étudiant/candidat à une formation."""
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "program_id", "academic_year", name="uq_user_program_academic_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), index=True)
    academic_year: Mapped[str] = mapped_column(String(9), index=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=ApplicationStatus.draft,
        index=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="applications")
    program: Mapped[Program] = relationship(back_populates="applications")
    documents: Mapped[list["Document"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    interview: Mapped["InterviewAppointment | None"] = relationship(
        back_populates="application", cascade="all, delete-orphan", uselist=False
    )
    interview_result: Mapped["InterviewResult | None"] = relationship(
        back_populates="application", cascade="all, delete-orphan", uselist=False
    )


class InterviewAppointment(Base):
    """Rendez-vous et convocations aux entretiens d'évaluation et de sélection."""
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), unique=True, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    interview_type: Mapped[InterviewType] = mapped_column(
        Enum(InterviewType, name="interview_type", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=InterviewType.en_ligne
    )
    location_or_link: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=InterviewStatus.programme,
        index=True
    )
    interviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="interview")
    interviewer: Mapped[User | None] = relationship()
    result: Mapped["InterviewResult | None"] = relationship(
        back_populates="interview", cascade="all, delete-orphan", uselist=False
    )


class InterviewResult(Base):
    """Résultats, évaluations et grille de notation du jury après entretien."""
    __tablename__ = "interview_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), unique=True, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), unique=True, index=True
    )
    technical_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    motivation_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    language_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    decision: Mapped[JuryDecision] = mapped_column(
        Enum(JuryDecision, name="jury_decision", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=JuryDecision.favorable,
        index=True
    )
    jury_feedback: Mapped[str] = mapped_column(Text, default="")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    interview: Mapped[InterviewAppointment] = relationship(back_populates="result")
    application: Mapped[Application] = relationship(back_populates="interview_result")


# =====================================================================
# SA-14 : Documents, Versions & Synchronisation Vectorielle
# =====================================================================

class Document(Base):
    """Fichiers et pièces jointes (dossiers de candidatures, documents académiques)."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=DocumentType.autre,
        index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500), default="")
    mime_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application | None] = relationship(back_populates="documents")
    user: Mapped[User | None] = relationship(back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersion.version_number"
    )


class DocumentVersion(Base):
    """Historique des différentes versions d'un document importé ou révisé."""
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    change_summary: Mapped[str] = mapped_column(String(255), default="Dépôt initial")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document] = relationship(back_populates="versions")


class VectorSyncTask(Base):
    """Suivi des traitements automatiques de vectorisation (RAG / embeddings base vectorielle)."""
    __tablename__ = "vector_sync_tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    action: Mapped[VectorSyncAction] = mapped_column(
        Enum(VectorSyncAction, name="vector_sync_action", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=VectorSyncAction.upsert,
        index=True
    )
    status: Mapped[VectorSyncStatus] = mapped_column(
        Enum(VectorSyncStatus, name="vector_sync_status", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=VectorSyncStatus.pending,
        index=True
    )
    embedding_model: Mapped[str] = mapped_column(String(100), default="text-embedding-3-small")
    collection_name: Mapped[str] = mapped_column(String(100), default="smartcampus_documents")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    vector_dimensions: Mapped[int] = mapped_column(Integer, default=1536)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped[Document | None] = relationship()


class SyncLog(Base):
    """Journal de synchronisation global (catalogue, référentiels, RAG embeddings)."""
    __tablename__ = "sync_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="sync_status", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=SyncStatus.in_progress,
        index=True
    )
    records_synced: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
