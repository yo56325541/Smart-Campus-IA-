import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import ClassVar, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .models import ApplicationStatus, Institution, Role


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


class ProgramOut(ORM, ProgramIn):
    id: uuid.UUID


class ProgramDetail(ProgramOut):
    conditions: list[ConditionOut] = []
    tariffs: list[TariffOut] = []


# ---------- Candidatures (SA-13) ----------

class ApplicationIn(BaseModel):
    """Dépôt d'une candidature par un candidat."""
    program_id: uuid.UUID
    academic_year: str = Field(pattern=r"^\d{4}-\d{4}$")
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("academic_year")
    @classmethod
    def _validate_academic_year(cls, v: str) -> str:
        return validate_academic_year(v)


class ApplicationStatusIn(BaseModel):
    """Mise à jour du statut d'une candidature (réservé admin)."""
    status: ApplicationStatus
    notes: Optional[str] = Field(default=None, max_length=2000)


class ApplicationOut(ORM):
    id: uuid.UUID
    user_id: uuid.UUID
    program_id: uuid.UUID
    academic_year: str
    status: ApplicationStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationOut):
    """Vue enrichie avec le résumé de la formation et de l'utilisateur."""
    program_name: Optional[str] = None
    program_slug: Optional[str] = None
    applicant_email: Optional[str] = None
    applicant_name: Optional[str] = None
