"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Trash2, ClipboardList } from "lucide-react";
import { AdminPageHeader } from "@/components/admin/AdminPageHeader";
import { useCampus } from "@/components/providers/CampusProvider";
import { Alert } from "@/components/ui/Alert";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Input";
import {
  CampusApiError,
  deleteAdminApplication,
  getAdminApplication,
  updateAdminApplicationStatus,
} from "@/lib/api/campus";
import type {
  ApplicationDetail,
  ApplicationStatus,
} from "@/lib/types";

const statuses: { value: ApplicationStatus; label: string }[] = [
  { value: "draft", label: "Brouillon" },
  { value: "submitted", label: "Soumise" },
  { value: "under_review", label: "En cours d’examen" },
  { value: "accepted", label: "Acceptée" },
  { value: "rejected", label: "Refusée" },
];

function formatDate(value: string) {
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function AdminApplicationDetailPage() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const router = useRouter();
  const { accessToken } = useCampus();
  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [status, setStatus] = useState<ApplicationStatus>("submitted");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchApplication = useCallback(async () => {
    if (!accessToken) {
      throw new Error("La session administrateur est absente. Reconnectez-vous.");
    }
    return getAdminApplication(applicationId, accessToken);
  }, [accessToken, applicationId]);

  const loadApplication = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchApplication();
      setApplication(result);
      setStatus(result.status);
    } catch (requestError) {
      setError(
        requestError instanceof CampusApiError || requestError instanceof Error
          ? requestError.message
          : "Impossible de charger cette candidature.",
      );
      setApplication(null);
    } finally {
      setLoading(false);
    }
  }, [fetchApplication]);

  useEffect(() => {
    let active = true;
    void Promise.resolve()
      .then(fetchApplication)
      .then((result) => {
        if (active) {
          setApplication(result);
          setStatus(result.status);
        }
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        setError(
          requestError instanceof CampusApiError || requestError instanceof Error
            ? requestError.message
            : "Impossible de charger cette candidature.",
        );
        setApplication(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fetchApplication]);

  async function handleStatusSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !application) {
      setError("La session administrateur est absente. Reconnectez-vous.");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateAdminApplicationStatus(
        application.id,
        { status },
        accessToken,
      );
      setApplication((current) =>
        current ? { ...current, ...updated } : current,
      );
      setSuccess("Le statut de la candidature a été mis à jour.");
    } catch (requestError) {
      setError(
        requestError instanceof CampusApiError
          ? requestError.message
          : "La mise à jour du statut a échoué.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!accessToken || !application) {
      setError("La session administrateur est absente. Reconnectez-vous.");
      return;
    }
    const confirmed = window.confirm(
      "Cette suppression définitive ne peut pas être annulée. Supprimer la candidature ?",
    );
    if (!confirmed) return;

    setDeleting(true);
    setError(null);
    try {
      await deleteAdminApplication(application.id, accessToken);
      router.replace("/admin/candidatures");
    } catch (requestError) {
      setError(
        requestError instanceof CampusApiError
          ? requestError.message
          : "La suppression de la candidature a échoué.",
      );
      setDeleting(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <Link
        href="/admin/candidatures"
        className="mb-5 inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold text-navy-700 hover:bg-navy-50"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Retour aux candidatures
      </Link>
      <AdminPageHeader
        title="Détail de la candidature"
        description="Les informations ci-dessous proviennent de GET /admin/applications/{application_id}."
        icon={ClipboardList}
      />

      {error && (
        <Alert variant="error" title="Action impossible" className="mb-5">
          <p>{error}</p>
          {!application && (
            <Button className="mt-3" size="sm" onClick={() => void loadApplication()}>
              Réessayer
            </Button>
          )}
        </Alert>
      )}
      {success && (
        <Alert variant="success" title="Mise à jour effectuée" className="mb-5">
          {success}
        </Alert>
      )}

      {loading && (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.8fr)]" aria-live="polite">
          <Card className="h-56 animate-pulse bg-navy-50" />
          <Card className="h-56 animate-pulse bg-navy-50" />
        </div>
      )}

      {!loading && !application && !error && (
        <Card>
          <p className="text-center text-sm text-text-muted">
            Cette candidature n’est pas disponible.
          </p>
        </Card>
      )}

      {!loading && application && (
        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.8fr)]">
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold text-navy-800">
                  {application.applicant_name || "Candidat non renseigné"}
                </h2>
                <p className="mt-1 text-sm text-text-muted">
                  {application.applicant_email || "E-mail non renseigné"}
                </p>
              </div>
              <StatusBadge status={application.status} />
            </div>
            <dl className="mt-6 grid gap-5 border-t border-border pt-5 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">Formation</dt>
                <dd className="mt-1 font-medium text-navy-800">
                  {application.program_name || "Formation non renseignée"}
                </dd>
                {application.program_slug && (
                  <dd className="mt-1 text-xs text-text-muted">{application.program_slug}</dd>
                )}
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">Année académique</dt>
                <dd className="mt-1 font-medium text-navy-800">{application.academic_year}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">Créée le</dt>
                <dd className="mt-1 font-medium text-navy-800">{formatDate(application.created_at)}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">Dernière mise à jour</dt>
                <dd className="mt-1 font-medium text-navy-800">{formatDate(application.updated_at)}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">Note du dossier</dt>
                <dd className="mt-1 whitespace-pre-wrap text-sm leading-6 text-navy-800">
                  {application.notes || "Aucune note renseignée."}
                </dd>
              </div>
            </dl>
            <p className="mt-5 break-all text-xs text-text-muted">
              Identifiant : {application.id}
            </p>
          </Card>

          <div className="space-y-5">
            <Card>
              <h2 className="text-lg font-bold text-navy-800">Statut du dossier</h2>
              <p className="mt-1 text-sm leading-6 text-text-muted">
                Le statut est modifié par PATCH /admin/applications/{`{application_id}`}/status.
              </p>
              <form className="mt-5 space-y-4" onSubmit={handleStatusSubmit}>
                <Select
                  label="Nouveau statut"
                  value={status}
                  onChange={(event) => setStatus(event.target.value as ApplicationStatus)}
                >
                  {statuses.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </Select>
                <Button type="submit" fullWidth loading={saving}>
                  Enregistrer le statut
                </Button>
              </form>
            </Card>

            <Card className="border-red-200">
              <Badge variant="danger" className="mb-3">Action définitive</Badge>
              <h2 className="text-lg font-bold text-navy-800">Supprimer le dossier</h2>
              <p className="mt-2 text-sm leading-6 text-text-muted">
                Le Backend supprime définitivement la candidature et son historique. Cette action est irréversible.
              </p>
              <Button
                type="button"
                variant="danger"
                className="mt-4"
                fullWidth
                loading={deleting}
                leftIcon={<Trash2 className="h-4 w-4" />}
                onClick={() => void handleDelete()}
              >
                Supprimer définitivement
              </Button>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
