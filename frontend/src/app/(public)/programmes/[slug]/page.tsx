import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  Clock3,
  GraduationCap,
  Languages,
  Wallet,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import {
  getAdmissionConditions,
  getProgram,
  getTariffs,
  ProgramApiError,
} from "@/lib/api/programs";

type ProgramPageProps = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({
  params,
}: ProgramPageProps): Promise<Metadata> {
  const { slug } = await params;
  try {
    const program = await getProgram(slug);
    return {
      title: program.name,
      description: program.description || `Détails de la formation ${program.name}.`,
    };
  } catch (error) {
    if (error instanceof ProgramApiError && error.status === 404) {
      return { title: "Formation introuvable" };
    }
    throw error;
  }
}

function formatAmount(amount: string, currency: string) {
  const value = Number(amount);
  if (!Number.isFinite(value)) return `${amount} ${currency}`;

  return new Intl.NumberFormat("fr-TN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDuration(years: number | null) {
  if (years === null) return "Non renseignée";
  return `${years} ${years > 1 ? "ans" : "an"}`;
}

export default function ProgramDetailPage({ params }: ProgramPageProps) {
  return (
    <Suspense
      fallback={
        <div className="container-page py-16 text-center" role="status">
          Chargement des informations de la formation...
        </div>
      }
    >
      <ProgramDetailContent params={params} />
    </Suspense>
  );
}

async function ProgramDetailContent({ params }: ProgramPageProps) {
  const { slug } = await params;
  let program;
  let conditions;
  let tariffs;

  try {
    [program, conditions, tariffs] = await Promise.all([
      getProgram(slug),
      getAdmissionConditions(slug),
      getTariffs(slug),
    ]);
  } catch (error) {
    if (error instanceof ProgramApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return (
    <div className="min-h-full bg-bg">
      <section className="bg-navy-800 py-10 text-white sm:py-14">
        <div className="container-page">
          <Link
            href="/programmes"
            className="mb-7 inline-flex min-h-10 items-center gap-2 text-sm font-medium text-navy-200 transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-400"
          >
            <ArrowLeft className="h-4 w-4" />
            Retour au catalogue
          </Link>
          <div className="max-w-4xl">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{program.institution}</Badge>
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold capitalize text-navy-100">
                {program.level.replace(/[_-]+/g, " ")}
              </span>
            </div>
            <h1 className="mb-4 text-3xl font-bold text-white sm:text-4xl">
              {program.name}
            </h1>
            <p className="max-w-3xl leading-relaxed text-navy-200">
              {program.description || "Aucune description disponible pour cette formation."}
            </p>
          </div>
        </div>
      </section>

      <div className="container-page py-8 sm:py-10">
        <section aria-label="Informations générales" className="mb-8 grid gap-4 sm:grid-cols-3">
          <Card className="flex items-center gap-4">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-turquoise-50 text-turquoise-700">
              <GraduationCap className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs font-medium text-text-muted">Niveau</p>
              <p className="font-semibold capitalize text-navy-800">
                {program.level.replace(/[_-]+/g, " ")}
              </p>
            </div>
          </Card>
          <Card className="flex items-center gap-4">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-turquoise-50 text-turquoise-700">
              <Clock3 className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs font-medium text-text-muted">Durée</p>
              <p className="font-semibold text-navy-800">
                {formatDuration(program.duration_years)}
              </p>
            </div>
          </Card>
          <Card className="flex items-center gap-4">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-turquoise-50 text-turquoise-700">
              <Languages className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs font-medium text-text-muted">Langue</p>
              <p className="font-semibold text-navy-800">
                {program.language.toLocaleUpperCase("fr")}
              </p>
            </div>
          </Card>
        </section>

        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.8fr)]">
          <section aria-labelledby="admission-title">
            <div className="mb-4 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-turquoise-700" />
              <h2 id="admission-title" className="text-xl font-bold text-navy-800">
                Conditions d’admission
              </h2>
            </div>
            {conditions.length === 0 ? (
              <Card>
                <p className="text-sm leading-relaxed text-text-muted">
                  Les conditions d’admission de cette formation ne sont pas
                  encore renseignées.
                </p>
              </Card>
            ) : (
              <ol className="flex flex-col gap-3">
                {conditions.map((condition) => (
                  <li key={condition.id}>
                    <Card>
                      <h3 className="font-semibold text-navy-800">
                        {condition.title}
                      </h3>
                      {condition.description && (
                        <p className="mt-2 text-sm leading-relaxed text-text-muted">
                          {condition.description}
                        </p>
                      )}
                      {(condition.required_diploma || condition.min_average) && (
                        <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-2 border-t border-border pt-3 text-sm">
                          {condition.required_diploma && (
                            <div>
                              <dt className="text-xs text-text-muted">
                                Diplôme requis
                              </dt>
                              <dd className="font-medium text-navy-800">
                                {condition.required_diploma}
                              </dd>
                            </div>
                          )}
                          {condition.min_average && (
                            <div>
                              <dt className="text-xs text-text-muted">
                                Moyenne minimale
                              </dt>
                              <dd className="font-medium text-navy-800">
                                {condition.min_average}/20
                              </dd>
                            </div>
                          )}
                        </dl>
                      )}
                    </Card>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section aria-labelledby="tariffs-title">
            <div className="mb-4 flex items-center gap-2">
              <Wallet className="h-5 w-5 text-turquoise-700" />
              <h2 id="tariffs-title" className="text-xl font-bold text-navy-800">
                Tarifs
              </h2>
            </div>
            {tariffs.length === 0 ? (
              <Card>
                <p className="text-sm leading-relaxed text-text-muted">
                  Les tarifs de cette formation ne sont pas encore renseignés.
                </p>
              </Card>
            ) : (
              <div className="flex flex-col gap-3">
                {tariffs.map((tariff) => (
                  <Card key={tariff.id}>
                    <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-navy-700">
                      <CalendarDays className="h-4 w-4 text-turquoise-700" />
                      Année universitaire {tariff.academic_year}
                    </div>
                    <p className="text-2xl font-bold text-navy-800">
                      {formatAmount(tariff.amount, tariff.currency)}
                    </p>
                    {tariff.registration_fee !== null && (
                      <p className="mt-2 text-sm text-text-muted">
                        Frais d’inscription :{" "}
                        <span className="font-medium text-navy-800">
                          {formatAmount(tariff.registration_fee, tariff.currency)}
                        </span>
                      </p>
                    )}
                    {tariff.payment_terms && (
                      <p className="mt-3 border-t border-border pt-3 text-sm leading-relaxed text-text-muted">
                        {tariff.payment_terms}
                      </p>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </section>
        </div>

        {program.careers && (
          <section aria-labelledby="careers-title" className="mt-8">
            <Card>
              <div className="mb-3 flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-turquoise-700" />
                <h2 id="careers-title" className="text-lg font-bold text-navy-800">
                  Débouchés
                </h2>
              </div>
              <p className="text-sm leading-relaxed text-text-muted">
                {program.careers}
              </p>
            </Card>
          </section>
        )}
      </div>
    </div>
  );
}
