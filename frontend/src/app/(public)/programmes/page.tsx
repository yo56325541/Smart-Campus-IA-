import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import {
  ArrowRight,
  BookOpen,
  Building2,
  Clock3,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { getPrograms } from "@/lib/api/programs";
import type { Institution } from "@/lib/types";

export const metadata: Metadata = {
  title: "Catalogue des formations",
  description:
    "Recherchez et comparez les formations de l’IIT et de l’ISB.",
};

const PAGE_SIZE = 24;
const INSTITUTIONS: Institution[] = ["IIT", "ISB"];

type SearchParams = Record<string, string | string[] | undefined>;

function firstParam(value: string | string[] | undefined) {
  return typeof value === "string" ? value : "";
}

function formatLevel(level: string) {
  return level
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toLocaleUpperCase("fr"));
}

function formatDuration(years: number | null) {
  if (years === null) return null;
  return `${years} ${years > 1 ? "ans" : "an"}`;
}

function getPaginationHref(
  offset: number,
  filters: { q: string; institution: string; level: string },
) {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.institution) params.set("institution", filters.institution);
  if (filters.level) params.set("level", filters.level);
  if (offset > 0) params.set("offset", String(offset));
  const query = params.toString();
  return `/programmes${query ? `?${query}` : ""}`;
}

export default function ProgramsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  return (
    <Suspense
      fallback={
        <div className="container-page py-16 text-center" role="status">
          Chargement du catalogue des formations...
        </div>
      }
    >
      <ProgramsContent searchParams={searchParams} />
    </Suspense>
  );
}

async function ProgramsContent({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const q = firstParam(params.q).trim();
  const institution = firstParam(params.institution);
  const level = firstParam(params.level).trim();
  const requestedOffset = Number(firstParam(params.offset) || "0");
  const offset =
    Number.isSafeInteger(requestedOffset) && requestedOffset >= 0
      ? requestedOffset
      : 0;
  const validInstitution = INSTITUTIONS.includes(institution as Institution)
    ? (institution as Institution)
    : undefined;

  const programs = await getPrograms({
    q: q || undefined,
    institution: validInstitution,
    level: level || undefined,
    limit: PAGE_SIZE + 1,
    offset,
  });
  const hasNextPage = programs.length > PAGE_SIZE;
  const visiblePrograms = programs.slice(0, PAGE_SIZE);
  const activeFilters = { q, institution: validInstitution ?? "", level };

  return (
    <div className="min-h-full bg-bg">
      <section className="bg-navy-800 py-12 text-white sm:py-16">
        <div className="container-page">
          <div className="max-w-3xl">
            <Badge variant="secondary" className="mb-4">
              Orientation universitaire
            </Badge>
            <h1 className="mb-4 text-3xl font-bold text-white sm:text-4xl">
              Catalogue des formations
            </h1>
            <p className="max-w-2xl leading-relaxed text-navy-200">
              Explorez les programmes de l’IIT et de l’ISB. Recherchez une
              formation et consultez les informations d’admission et de tarifs
              publiées.
            </p>
          </div>
        </div>
      </section>

      <section className="container-page py-8 sm:py-10">
        <Card className="mb-8">
          <div className="mb-5 flex items-center gap-2">
            <SlidersHorizontal className="h-5 w-5 text-turquoise-700" />
            <h2 className="text-lg font-bold text-navy-800">
              Rechercher et filtrer
            </h2>
          </div>
          <form
            action="/programmes"
            method="get"
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:items-end"
          >
            <label className="flex flex-col gap-1.5 text-sm font-medium text-navy-800 lg:col-span-2">
              Recherche
              <span className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                <input
                  type="search"
                  name="q"
                  defaultValue={q}
                  placeholder="Nom ou description"
                  className="h-11 w-full rounded-lg border border-border bg-white pl-10 pr-3 text-sm text-text outline-none transition focus:border-turquoise-500 focus:ring-2 focus:ring-turquoise-500/20"
                />
              </span>
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-navy-800">
              Établissement
              <select
                name="institution"
                defaultValue={validInstitution ?? ""}
                className="h-11 w-full rounded-lg border border-border bg-white px-3 text-sm text-text outline-none transition focus:border-turquoise-500 focus:ring-2 focus:ring-turquoise-500/20"
              >
                <option value="">Tous les établissements</option>
                <option value="IIT">IIT</option>
                <option value="ISB">ISB</option>
              </select>
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-navy-800">
              Niveau
              <input
                type="search"
                name="level"
                defaultValue={level}
                placeholder="Ex. licence, prepa"
                className="h-11 w-full rounded-lg border border-border bg-white px-3 text-sm text-text outline-none transition focus:border-turquoise-500 focus:ring-2 focus:ring-turquoise-500/20"
              />
            </label>
            <div className="flex gap-3 sm:col-span-2 lg:col-span-4">
              <Button type="submit" variant="primary" leftIcon={<Search className="h-4 w-4" />}>
                Appliquer les filtres
              </Button>
              <Link
                href="/programmes"
                className="inline-flex min-h-10 items-center rounded-lg px-4 text-sm font-semibold text-navy-700 transition hover:bg-navy-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500"
              >
                Effacer
              </Link>
            </div>
          </form>
        </Card>

        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-navy-800">
              {q || validInstitution || level
                ? "Résultats de votre recherche"
                : "Toutes les formations"}
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              {visiblePrograms.length > 0
                ? `${offset + 1}–${offset + visiblePrograms.length} formation${visiblePrograms.length > 1 ? "s" : ""}`
                : "Consultez le catalogue de l’IIT et de l’ISB."}
            </p>
          </div>
        </div>

        {visiblePrograms.length === 0 ? (
          <Card className="py-12 text-center sm:py-16">
            <span className="mx-auto mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-navy-50 text-navy-600">
              <BookOpen className="h-7 w-7" />
            </span>
            <h2 className="mb-2 text-xl font-bold text-navy-800">
              Aucune formation disponible
            </h2>
            <p className="mx-auto max-w-lg text-sm leading-relaxed text-text-muted">
              {q || validInstitution || level
                ? "Aucune formation ne correspond à ces critères. Modifiez votre recherche ou effacez les filtres."
                : "Le catalogue ne contient actuellement aucune formation. Les programmes seront affichés ici dès qu’ils seront disponibles."}
            </p>
            {(q || validInstitution || level) && (
              <Link href="/programmes" className="mt-5 inline-block">
                <Button variant="outline">Effacer les filtres</Button>
              </Link>
            )}
          </Card>
        ) : (
          <>
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {visiblePrograms.map((program) => (
                <Card
                  key={program.id}
                  className="flex h-full flex-col"
                  hoverable
                >
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <Badge variant="secondary">
                      {program.institution}
                    </Badge>
                    <span className="rounded-full bg-navy-50 px-3 py-1 text-xs font-semibold capitalize text-navy-700">
                      {formatLevel(program.level)}
                    </span>
                  </div>
                  <h3 className="mb-2 text-lg font-bold text-navy-800">
                    {program.name}
                  </h3>
                  <p className="mb-5 line-clamp-3 flex-1 text-sm leading-relaxed text-text-muted">
                    {program.description || "Aucune description disponible."}
                  </p>
                  <div className="mb-5 flex flex-wrap gap-x-4 gap-y-2 border-t border-border pt-4 text-sm text-text-muted">
                    <span className="inline-flex items-center gap-1.5">
                      <Building2 className="h-4 w-4 text-turquoise-700" />
                      {program.institution}
                    </span>
                    {formatDuration(program.duration_years) && (
                      <span className="inline-flex items-center gap-1.5">
                        <Clock3 className="h-4 w-4 text-turquoise-700" />
                        {formatDuration(program.duration_years)}
                      </span>
                    )}
                  </div>
                  <Link
                    href={`/programmes/${encodeURIComponent(program.slug)}`}
                    className="inline-flex min-h-11 items-center gap-2 font-semibold text-turquoise-700 hover:text-turquoise-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500"
                  >
                    Découvrir cette formation
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Card>
              ))}
            </div>
            {(offset > 0 || hasNextPage) && (
              <nav
                aria-label="Pagination du catalogue"
                className="mt-8 flex items-center justify-between gap-4"
              >
                {offset > 0 ? (
                  <Link
                    href={getPaginationHref(
                      Math.max(0, offset - PAGE_SIZE),
                      activeFilters,
                    )}
                  >
                    <Button variant="outline">Page précédente</Button>
                  </Link>
                ) : (
                  <span />
                )}
                {hasNextPage && (
                  <Link
                    href={getPaginationHref(offset + PAGE_SIZE, activeFilters)}
                  >
                    <Button variant="outline">Page suivante</Button>
                  </Link>
                )}
              </nav>
            )}
          </>
        )}
      </section>
    </div>
  );
}
