import type { ApplicationStatus } from "@/lib/types";

export const applicationStatusLabels: Record<ApplicationStatus, string> = {
  draft: "Brouillon",
  submitted: "Soumise",
  under_review: "En cours d’examen",
  accepted: "Acceptée",
  rejected: "Refusée",
};

export function formatCandidateDate(value: string | null | undefined) {
  if (!value) return "Non renseignée";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date indisponible";

  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(date);
}

export function getCandidateErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Une erreur inattendue est survenue. Réessayez.";
}
