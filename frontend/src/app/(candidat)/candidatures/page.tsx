"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, FileText } from "lucide-react";
import { Alert, ApiErrorAlert } from "@/components/ui/Alert";
import { CandidatePageHeader } from "@/components/candidate/CandidatePageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { CenteredSpinner } from "@/components/ui/Spinner";
import { useCampus } from "@/components/providers/CampusProvider";
import {
  createApplication,
  getMyApplications,
  withdrawApplication,
} from "@/lib/api/campus";
import { getPrograms } from "@/lib/api/programs";
import {
  applicationStatusLabels,
  formatCandidateDate,
  getCandidateErrorMessage,
} from "@/lib/candidate";
import type { ApplicationOut, ProgramOut } from "@/lib/types";

export default function CandidateApplicationsPage() {
  const { accessToken } = useCampus();
  const [applications, setApplications] = useState<ApplicationOut[] | null>(
    null,
  );
  const [applicationsLoading, setApplicationsLoading] = useState(true);
  const [applicationsError, setApplicationsError] = useState<string | null>(
    null,
  );
  const [programs, setPrograms] = useState<ProgramOut[] | null>(null);
  const [programsLoading, setProgramsLoading] = useState(true);
  const [programsError, setProgramsError] = useState<string | null>(null);
  const [programId, setProgramId] = useState("");
  const [academicYear, setAcademicYear] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [withdrawingId, setWithdrawingId] = useState<string | null>(null);

  const fetchApplications = useCallback(() => {
    if (!accessToken) {
      return Promise.reject(
        new Error("La session candidat n’est pas disponible."),
      );
    }
    return getMyApplications(accessToken);
  }, [accessToken]);

  async function reloadApplications() {
    setApplicationsLoading(true);
    setApplicationsError(null);
    try {
      setApplications(await fetchApplications());
    } catch (error) {
      setApplicationsError(getCandidateErrorMessage(error));
    } finally {
      setApplicationsLoading(false);
    }
  }

  const programsById = useMemo(
    () => new Map((programs ?? []).map((program) => [program.id, program])),
    [programs],
  );

  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    void fetchApplications()
      .then((result) => {
        if (active) {
          setApplications(result);
          setApplicationsError(null);
        }
      })
      .catch((error: unknown) => {
        if (active) setApplicationsError(getCandidateErrorMessage(error));
      })
      .finally(() => {
        if (active) setApplicationsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [accessToken, fetchApplications]);

  useEffect(() => {
    let active = true;
    void getPrograms({ limit: 200 })
      .then((result) => {
        if (active) setPrograms(result);
      })
      .catch((error: unknown) => {
        if (active) setProgramsError(getCandidateErrorMessage(error));
      })
      .finally(() => {
        if (active) setProgramsLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setSuccess(null);

    const yearMatch = /^(\d{4})-(\d{4})$/.exec(academicYear.trim());
    if (!yearMatch || Number(yearMatch[2]) !== Number(yearMatch[1]) + 1) {
      setFormError(
        "Saisissez une année universitaire au format AAAA-AAAA, avec deux années consécutives.",
      );
      return;
    }
    if (!accessToken) {
      setFormError("La session candidat n’est pas disponible.");
      return;
    }

    setSubmitting(true);
    try {
      const application = await createApplication(
        {
          program_id: programId,
          academic_year: academicYear.trim(),
          notes: notes.trim() || undefined,
        },
        accessToken,
      );
      setApplicationsError(null);
      setApplications((current) =>
        [application, ...(current ?? [])].filter(
          (item, index, list) =>
            list.findIndex((candidate) => candidate.id === item.id) === index,
        ),
      );
      setAcademicYear("");
      setNotes("");
      setSuccess("Votre candidature a été enregistrée par le Backend.");
    } catch (error) {
      setFormError(getCandidateErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleWithdrawal(application: ApplicationOut) {
    if (application.status !== "draft" || !accessToken) return;
    if (!window.confirm("Retirer cette candidature en brouillon ?")) return;

    setWithdrawingId(application.id);
    setActionError(null);
    setSuccess(null);
    try {
      await withdrawApplication(application.id, accessToken);
      setApplications((current) =>
        current?.filter((item) => item.id !== application.id) ?? [],
      );
      setSuccess("La candidature en brouillon a été retirée.");
    } catch (error) {
      setActionError(getCandidateErrorMessage(error));
    } finally {
      setWithdrawingId(null);
    }
  }

  return (
    <div>
      <CandidatePageHeader
        title="Mes candidatures"
        description="Consultez les candidatures retournées par le Backend ou déposez-en une pour une formation active."
      />

      {success && (
        <Alert className="mb-5" variant="success" title="Opération confirmée">
          {success}
        </Alert>
      )}
      {actionError && (
        <ApiErrorAlert message={actionError} className="mb-5" />
      )}

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)]">
        <Card>
          <h2 className="text-lg font-bold text-navy-800">
            Déposer une candidature
          </h2>
          <p className="mt-1 text-sm leading-relaxed text-text-muted">
            Les champs suivent le schéma accepté par le Backend. Une seule
            candidature est permise par formation et année universitaire.
          </p>

          {programsError && (
            <ApiErrorAlert message={programsError} className="mt-4" />
          )}
          {formError && (
            <ApiErrorAlert message={formError} className="mt-4" />
          )}
          {programs === null && !programsLoading && !programsError && (
            <Alert className="mt-4" variant="warning">
              Le catalogue n’a retourné aucune donnée exploitable.
            </Alert>
          )}
          {programs?.length === 0 && (
            <Alert className="mt-4" variant="info">
              Aucune formation active n’est disponible. Le dépôt de candidature
              sera possible lorsqu’une formation sera publiée.
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <label className="block text-sm font-medium text-navy-800">
              Formation
              <select
                required
                value={programId}
                onChange={(event) => setProgramId(event.target.value)}
                disabled={programsLoading || !programs?.length}
                className="mt-1.5 h-11 w-full rounded-lg border border-border bg-white px-3 text-sm outline-none focus:border-turquoise-500 focus:ring-2 focus:ring-turquoise-500/20 disabled:bg-navy-50"
              >
                <option value="">
                  {programsLoading
                    ? "Chargement des formations..."
                    : "Sélectionner une formation"}
                </option>
                {programs?.map((program) => (
                  <option key={program.id} value={program.id}>
                    {program.name} — {program.institution}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm font-medium text-navy-800">
              Année universitaire
              <input
                required
                value={academicYear}
                onChange={(event) => setAcademicYear(event.target.value)}
                placeholder="2026-2027"
                pattern="\d{4}-\d{4}"
                maxLength={9}
                inputMode="numeric"
                aria-describedby="application-year-hint"
                className="mt-1.5 h-11 w-full rounded-lg border border-border bg-white px-3 text-sm outline-none focus:border-turquoise-500 focus:ring-2 focus:ring-turquoise-500/20"
              />
              <span
                id="application-year-hint"
                className="mt-1 block text-xs text-text-muted"
              >
                Format AAAA-AAAA; l’année de fin doit suivre celle de début.
              </span>
            </label>

            <label className="block text-sm font-medium text-navy-800">
              Note (facultative)
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                maxLength={2000}
                rows={4}
                className="mt-1.5 w-full resize-y rounded-lg border border-border bg-white px-3 py-2 text-sm outline-none focus:border-turquoise-500 focus:ring-2 focus:ring-turquoise-500/20"
              />
              <span className="mt-1 block text-right text-xs text-text-muted">
                {notes.length}/2000
              </span>
            </label>

            <Button
              type="submit"
              fullWidth
              loading={submitting}
              disabled={
                programsLoading ||
                applicationsLoading ||
                !programs?.length ||
                !programId
              }
            >
              Envoyer ma candidature
            </Button>
          </form>
        </Card>

        <section aria-labelledby="applications-list-title">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2
                id="applications-list-title"
                className="text-xl font-bold text-navy-800"
              >
                Candidatures enregistrées
              </h2>
              <p className="mt-1 text-sm text-text-muted">
                État communiqué par le Backend.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void reloadApplications()}
              disabled={applicationsLoading}
              className="min-h-10 rounded-lg px-3 text-sm font-semibold text-turquoise-700 hover:bg-turquoise-50 disabled:opacity-50"
            >
              Actualiser
            </button>
          </div>

          {applicationsLoading ? (
            <CenteredSpinner label="Chargement des candidatures..." />
          ) : applicationsError ? (
            <div>
              <ApiErrorAlert message={applicationsError} />
              <button
                type="button"
                onClick={() => void reloadApplications()}
                className="mt-4 min-h-10 rounded-lg bg-navy-800 px-4 text-sm font-semibold text-white hover:bg-navy-700"
              >
                Réessayer
              </button>
            </div>
          ) : applications?.length === 0 ? (
            <Card className="py-10 text-center">
              <FileText className="mx-auto h-8 w-8 text-navy-400" />
              <h3 className="mt-3 font-semibold text-navy-800">
                Aucune candidature enregistrée
              </h3>
              <p className="mt-1 text-sm text-text-muted">
                Les candidatures confirmées par le Backend apparaîtront ici.
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {applications?.map((application) => {
                const program = programsById.get(application.program_id);
                return (
                  <Card key={application.id} className="p-5">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <h3 className="break-words font-bold text-navy-800">
                          {program?.name ?? "Formation associée"}
                        </h3>
                        <p className="mt-1 text-sm text-text-muted">
                          Année universitaire {application.academic_year}
                          {program ? ` · ${program.institution}` : ""}
                        </p>
                        <p className="mt-2 text-sm font-medium text-navy-700">
                          Statut : {applicationStatusLabels[application.status]}
                        </p>
                        <p className="mt-1 text-xs text-text-muted">
                          Créée le {formatCandidateDate(application.created_at)}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-wrap items-center gap-2">
                        <Link
                          href={`/candidatures/${encodeURIComponent(application.id)}`}
                          className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold text-turquoise-700 hover:bg-turquoise-50"
                        >
                          Détails
                          <ArrowRight className="h-4 w-4" />
                        </Link>
                        {application.status === "draft" ? (
                          <Button
                            type="button"
                            variant="danger"
                            size="sm"
                            loading={withdrawingId === application.id}
                            disabled={withdrawingId !== null}
                            onClick={() => void handleWithdrawal(application)}
                          >
                            Retirer
                          </Button>
                        ) : (
                          <span className="text-xs text-text-muted">
                            Retrait indisponible après le brouillon
                          </span>
                        )}
                      </div>
                    </div>
                  </Card>
                );
              })}
              {applications?.length === 200 && (
                <p className="text-sm text-text-muted">
                  Seules les 200 candidatures les plus récentes sont chargées.
                </p>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
