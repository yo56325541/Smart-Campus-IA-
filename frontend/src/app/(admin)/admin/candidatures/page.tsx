"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Search, ClipboardList, ArrowRight } from "lucide-react";
import { AdminPageHeader } from "@/components/admin/AdminPageHeader";
import { useCampus } from "@/components/providers/CampusProvider";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Input";
import { StatusBadge } from "@/components/ui/Badge";
import { CampusApiError, getAdminApplications } from "@/lib/api/campus";
import type { ApplicationDetail, ApplicationStatus } from "@/lib/types";

const statuses: ApplicationStatus[] = [
  "draft",
  "submitted",
  "under_review",
  "accepted",
  "rejected",
];

function formatDate(value: string) {
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function AdminApplicationsPage() {
  const { accessToken } = useCampus();
  const [applications, setApplications] = useState<ApplicationDetail[] | null>(
    null,
  );
  const [status, setStatus] = useState<ApplicationStatus | "">("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApplications = useCallback(async () => {
    if (!accessToken) {
      throw new Error("La session administrateur est absente. Reconnectez-vous.");
    }
    return getAdminApplications(accessToken, {
      status: status || undefined,
      limit: 200,
    });
  }, [accessToken, status]);

  const loadApplications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setApplications(await fetchApplications());
    } catch (requestError) {
      setError(
        requestError instanceof CampusApiError || requestError instanceof Error
          ? requestError.message
          : "Impossible de charger les candidatures.",
      );
      setApplications(null);
    } finally {
      setLoading(false);
    }
  }, [fetchApplications]);

  useEffect(() => {
    let active = true;
    void Promise.resolve()
      .then(fetchApplications)
      .then((result) => {
        if (active) setApplications(result);
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        setError(
          requestError instanceof CampusApiError || requestError instanceof Error
            ? requestError.message
            : "Impossible de charger les candidatures.",
        );
        setApplications(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fetchApplications]);

  const visibleApplications = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("fr");
    if (!applications || !query) return applications ?? [];
    return applications.filter((application) =>
      [
        application.applicant_name ?? "",
        application.applicant_email ?? "",
        application.program_name ?? "",
        application.academic_year,
      ]
        .join(" ")
        .toLocaleLowerCase("fr")
        .includes(query),
    );
  }, [applications, search]);

  return (
    <div className="animate-fade-in">
      <AdminPageHeader
        title="Gestion des candidatures"
        description="Liste complète autorisée aux administrateurs, avec détails et statut issus des réponses Backend."
        icon={ClipboardList}
      />

      {error && (
        <Alert variant="error" title="Chargement impossible" className="mb-5">
          <p>{error}</p>
          <Button className="mt-3" size="sm" onClick={() => void loadApplications()}>
            Réessayer
          </Button>
        </Alert>
      )}

      <Card noPadding>
        <div className="grid gap-4 border-b border-border p-5 md:grid-cols-[minmax(12rem,1fr)_minmax(16rem,1.4fr)] md:items-end">
          <Select
            label="Filtrer par statut (Backend)"
            value={status}
            onChange={(event) => {
              setLoading(true);
              setError(null);
              setStatus(event.target.value as ApplicationStatus | "");
            }}
          >
            <option value="">Tous les statuts</option>
            {statuses.map((value) => (
              <option key={value} value={value}>
                {value === "draft"
                  ? "Brouillon"
                  : value === "submitted"
                    ? "Soumise"
                    : value === "under_review"
                      ? "En cours d’examen"
                      : value === "accepted"
                        ? "Acceptée"
                        : "Refusée"}
              </option>
            ))}
          </Select>
          <Input
            label="Rechercher dans les résultats chargés"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Nom, e-mail, formation ou année"
            leftIcon={<Search className="h-4 w-4" />}
          />
        </div>

        <p className="px-5 pt-4 text-xs text-text-muted">
          {applications?.length === 200
            ? "Les 200 candidatures les plus récentes du filtre sélectionné sont chargées."
            : applications
              ? `${applications.length} candidature${applications.length === 1 ? "" : "s"} chargée${applications.length === 1 ? "" : "s"}.`
              : "Chargement…"}
        </p>

        {loading && (
          <div className="space-y-3 p-5" aria-live="polite">
            <div className="h-12 animate-pulse rounded-lg bg-navy-50" />
            <div className="h-12 animate-pulse rounded-lg bg-navy-50" />
          </div>
        )}

        {!loading && applications?.length === 0 && (
          <p className="p-8 text-center text-sm text-text-muted">
            Aucune candidature n’est disponible pour ce filtre.
          </p>
        )}

        {!loading && applications && applications.length > 0 && visibleApplications.length === 0 && (
          <p className="p-8 text-center text-sm text-text-muted">
            Aucun résultat chargé ne correspond à cette recherche.
          </p>
        )}

        {!loading && visibleApplications.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left text-sm">
              <thead className="bg-navy-50 text-xs uppercase tracking-wide text-navy-700">
                <tr>
                  <th scope="col" className="px-5 py-3">Candidat</th>
                  <th scope="col" className="px-5 py-3">Formation</th>
                  <th scope="col" className="px-5 py-3">Année</th>
                  <th scope="col" className="px-5 py-3">Statut</th>
                  <th scope="col" className="px-5 py-3">Créée le</th>
                  <th scope="col" className="px-5 py-3"><span className="sr-only">Détails</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {visibleApplications.map((application) => (
                  <tr key={application.id}>
                    <td className="px-5 py-4">
                      <p className="font-semibold text-navy-800">
                        {application.applicant_name || "Nom non renseigné"}
                      </p>
                      <p className="mt-1 text-xs text-text-muted">
                        {application.applicant_email || "E-mail non renseigné"}
                      </p>
                    </td>
                    <td className="px-5 py-4 text-navy-800">
                      {application.program_name || "Formation non renseignée"}
                    </td>
                    <td className="px-5 py-4 text-text-muted">
                      {application.academic_year}
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={application.status} size="sm" />
                    </td>
                    <td className="px-5 py-4 text-text-muted">
                      {formatDate(application.created_at)}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        href={`/admin/candidatures/${encodeURIComponent(application.id)}`}
                        className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold text-turquoise-700 hover:bg-turquoise-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500"
                      >
                        Détails
                        <ArrowRight className="h-4 w-4" aria-hidden="true" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
