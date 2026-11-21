"""Modèles SQLAlchemy pour SmartCampus AI.
Alignés avec le schéma partagé (SA-12, SA-13, SA-17, SA-25, SA-29).
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


class Role(str, enum.Enum):
    admin = "admin"
    candidat = "candidat"


class Institution(str, enum.Enum):
    IIT = "IIT"
    ISB = "ISB"


class ApplicationStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    accepted = "accepted"
    rejected = "rejected"


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

    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    institution: Mapped[Institution] = mapped_column(
        Enum(Institution, name="institution", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        index=True
    )
    level: Mapped[str] = mapped_column(String(50), index=True)  # licence | prepa | ingenierie | ...
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    duration_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String(50), default="fr")
    careers: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    conditions: Mapped[list["AdmissionCondition"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", order_by="AdmissionCondition.position"
    )
    tariffs: Mapped[list["Tariff"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", order_by="Tariff.academic_year"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )


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


class VisitorSession(Base):
    """Session anonyme visiteur. Seul le hash SHA-256 du jeton est conservé en base."""
    __tablename__ = "visitor_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)


class Conversation(Base):
    """Conversations de SmartCampus AI."""
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visitor_sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Application(Base):
    """Candidature d'un utilisateur à une formation pour une année académique donnée (SA-13)."""
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "program_id", "academic_year", name="uq_applications_user_program_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False, index=True)  # ex: "2026-2027"
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="applicationstatus",
             native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=ApplicationStatus.draft,
        nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="applications")
    program: Mapped[Program] = relationship(back_populates="applications")
