/**
 * Types TypeScript alignés sur les schémas Pydantic du Backend FastAPI.
 * Source : app/schemas.py · app/models.py
 *
 * NE PAS modifier sans synchronisation avec le backend.
 */

// ─── Enums ────────────────────────────────────────────────────────────────────

export type Role = "admin" | "candidat";

export type Institution = "IIT" | "ISB";

export type ApplicationStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "accepted"
  | "rejected";

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface UserOut {
  id: string;             // UUID
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string | null; // ISO 8601
}

export interface TokenOut {
  access_token: string;
  token_type: "bearer";
  user: UserOut;
  linked_conversations: number;
}

export interface RegisterIn {
  email: string;
  password: string;       // 8-128 chars
  full_name: string;      // 0-120 chars
}

export interface LoginIn {
  email: string;
  password: string;       // 1-128 chars
}

// ─── Sessions Visiteur ────────────────────────────────────────────────────────

export interface SessionOut {
  session_token: string;
  expires_at: string;     // ISO 8601
}

export interface SessionInfo {
  id: string;             // UUID
  expires_at: string;     // ISO 8601
  linked: boolean;
}

export interface LinkOut {
  linked_conversations: number;
}

// ─── Conversations ────────────────────────────────────────────────────────────

export interface ConversationIn {
  title: string;          // 0-200 chars
}

export interface ConversationOut {
  id: string;             // UUID
  title: string;
  session_id: string;     // UUID
  user_id: string | null; // UUID
  created_at: string;     // ISO 8601
}

// ─── Programmes ───────────────────────────────────────────────────────────────

export interface ProgramOut {
  id: string;             // UUID
  slug: string;           // regex: ^[a-z0-9]+(-[a-z0-9]+)*$
  institution: Institution;
  level: string;          // ex: "licence", "prepa", "ingenierie"
  name: string;
  description: string;
  duration_years: number | null; // 1-10
  language: string;       // ex: "fr"
  careers: string;
  is_active: boolean;
}

export interface ProgramIn {
  slug: string;
  institution: Institution;
  level: string;
  name: string;
  description?: string;
  duration_years?: number | null;
  language?: string;
  careers?: string;
  is_active?: boolean;
}

export interface ProgramUpdate {
  institution?: Institution;
  level?: string;
  name?: string;
  description?: string;
  duration_years?: number | null;
  language?: string;
  careers?: string;
  is_active?: boolean;
}

// ─── Conditions d'admission ───────────────────────────────────────────────────

export interface ConditionOut {
  id: string;             // UUID
  program_id: string;     // UUID
  title: string;
  description: string;
  required_diploma: string | null; // max 120 chars
  min_average: string | null;      // Decimal 0-20 → string en JSON
  position: number;
}

export interface ConditionIn {
  title: string;          // 1-200 chars
  description?: string;
  required_diploma?: string | null;
  min_average?: string | null;     // "0.00" - "20.00"
  position?: number;
}

export interface ConditionUpdate {
  title?: string;
  description?: string;
  required_diploma?: string | null;
  min_average?: string | null;
  position?: number;
}

// ─── Tarifs ───────────────────────────────────────────────────────────────────

export interface TariffOut {
  id: string;             // UUID
  program_id: string;     // UUID
  academic_year: string;  // ex: "2026-2027"
  amount: string;         // Decimal → string en JSON
  registration_fee: string | null;
  currency: string;       // 3 chars, ex: "TND"
  payment_terms: string | null;
}

export interface TariffIn {
  academic_year: string;  // regex: ^\d{4}-\d{4}$
  amount: string;
  registration_fee?: string | null;
  currency?: string;
  payment_terms?: string | null;
}

export interface TariffUpdate {
  amount?: string;
  registration_fee?: string | null;
  currency?: string;
  payment_terms?: string | null;
}

// ─── Détail Programme (inclut conditions + tarifs) ───────────────────────────

export interface ProgramDetail extends ProgramOut {
  conditions: ConditionOut[];
  tariffs: TariffOut[];
}

// ─── Candidatures ─────────────────────────────────────────────────────────────

export interface ApplicationOut {
  id: string;             // UUID
  user_id: string;        // UUID
  program_id: string;     // UUID
  academic_year: string;  // ex: "2026-2027"
  status: ApplicationStatus;
  notes: string | null;
  created_at: string;     // ISO 8601
  updated_at: string;     // ISO 8601
}

export interface ApplicationIn {
  program_id: string;     // UUID
  academic_year: string;  // ex: "2026-2027"
  notes?: string | null;  // max 2000 chars
}

export interface ApplicationDetail extends ApplicationOut {
  program_name: string | null;
  program_slug: string | null;
  applicant_email: string | null;
  applicant_name: string | null;
}

export interface ApplicationStatusIn {
  status: ApplicationStatus;
  notes?: string | null;
}

// ─── Admin Utilisateurs ───────────────────────────────────────────────────────

export interface AdminCreateUserIn {
  email: string;
  password: string;       // 8-128 chars
  full_name?: string;
  role?: Role;            // défaut: "candidat"
}

export interface UserActiveIn {
  is_active: boolean;
}

// ─── Réponses API Génériques ──────────────────────────────────────────────────

export interface ApiError {
  detail: string;
}

export interface PaginationParams {
  limit?: number;         // 1-200, défaut 50
  offset?: number;        // ≥0, défaut 0
}

// ─── Filtres Programmes ───────────────────────────────────────────────────────

export interface ProgramFilters extends PaginationParams {
  institution?: Institution;
  level?: string;
  q?: string;
  include_inactive?: boolean;
}

// ─── Filtres Candidatures ─────────────────────────────────────────────────────

export interface ApplicationFilters extends PaginationParams {
  academic_year?: string;
  status?: ApplicationStatus;
  program_id?: string;
  user_id?: string;
}
