"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { ApiErrorAlert } from "@/components/ui/Alert";
import { CandidatePageHeader } from "@/components/candidate/CandidatePageHeader";
import { Card } from "@/components/ui/Card";
import { CenteredSpinner } from "@/components/ui/Spinner";
import { useCampus } from "@/components/providers/CampusProvider";
import { getMyApplication } from "@/lib/api/campus";
import { getPrograms } from "@/lib/api/programs";
import {
  applicationStatusLabels,
  formatCandidateDate,
  getCandidateErrorMessage,
} from "@/lib/candidate";
import type { ApplicationOut, ProgramOut } from "@/lib/types";

export default function CandidateApplicationDetailPage() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const { accessToken } = useCampus();
  const [application, setApplication] = useState<ApplicationOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [program, setProgram] = useState<ProgramOut | null>(null);
  const [programError, setProgramError] = useState<string | null>(null);

  const fetchApplication = useCallback(async () => {
    if (!accessToken) {
      throw new Error("La session candidat n’est pas disponible.");
    }

    const application = await getMyApplication(applicationId, accessToken);
    try {
      const programs = await getPrograms({ limit: 200 });
      return {
        application,
        program: programs.find((item) => item.id === application.program_id) ?? null,
        programError: null,
      };
    } catch (reason) {
      return {
        application,
        program: null,
        programError: getCandidateErrorMessage(reason),
      };
    }
  }, [accessToken, applicationId]);

  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    void fetchApplication()
      .then((result) => {
        if (active) {
          setApplication(result.application);
          setProgram(result.program);
          setProgramError(result.programError);
          setError(null);
        }
      })
      .catch((reason: unknown) => {
        if (active) setError(getCandidateErrorMessage(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [accessToken, fetchApplication]);

  async function retryApplication() {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchApplication();
      setApplication(result.application);
      setProgram(result.program);
      setProgramError(result.programError);
    } catch (reason) {
      setError(getCandidateErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <Link
        href="/candidatures"
        className="mb-6 inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-turquoise-700 hover:text-turquoise-800"
      >
        <ArrowLeft className="h-4 w-4" />
        Retour aux candidatures
      </Link>
      <CandidatePageHeader
        title="Détail de la candidature"
        description="Les informations ci-dessous proviennent de la candidature retournée par le Backend."
      />

      {loading ? (
        <CenteredSpinner label="Chargement de la candidature..." />
      ) : error ? (
        <div>
          <ApiErrorAlert message={error} />
          <button
            type="button"
            onClick={() => void retryApplication()}
            className="mt-4 min-h-10 rounded-lg bg-navy-800 px-4 text-sm font-semibold text-white hover:bg-navy-700"
          >
            Réessayer
          </button>
        </div>
      ) : application ? (
        <div className="space-y-5">
          <Card>
            <h2 className="text-lg font-bold text-navy-800">
              {program?.name ?? "Formation associée"}
            </h2>
            <dl className="mt-5 grid gap-5 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Année universitaire
                </dt>
                <dd className="mt-1 font-medium text-navy-800">
                  {application.academic_year}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Statut
                </dt>
                <dd className="mt-1 font-medium text-navy-800">
                  {applicationStatusLabels[application.status]}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Créée le
                </dt>
                <dd className="mt-1 font-medium text-navy-800">
                  {formatCandidateDate(application.created_at)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Mise à jour le
                </dt>
                <dd className="mt-1 font-medium text-navy-800">
                  {formatCandidateDate(application.updated_at)}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Note
                </dt>
                <dd className="mt-1 whitespace-pre-wrap break-words text-sm text-navy-800">
                  {application.notes || "Aucune note n’a été transmise."}
                </dd>
              </div>
            </dl>
            {program && (
              <Link
                href={`/programmes/${encodeURIComponent(program.slug)}`}
                className="mt-5 inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-turquoise-700 hover:text-turquoise-800"
              >
                Consulter la formation, ses conditions et ses tarifs
                <ExternalLink className="h-4 w-4" />
              </Link>
            )}
            {programError && (
              <ApiErrorAlert message={programError} className="mt-4" />
            )}
            {!program && !programError && (
              <p className="mt-5 break-all text-xs text-text-muted">
                Identifiant de formation : {application.program_id}
              </p>
            )}
          </Card>
        </div>
      ) : (
        <Card>
          <p className="text-sm text-text-muted">
            Aucune donnée de candidature n’a été retournée.
          </p>
        </Card>
      )}
    </div>
  );
}
