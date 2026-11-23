"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  ClipboardList,
  Users,
} from "lucide-react";
import { AdminPageHeader } from "@/components/admin/AdminPageHeader";
import { FeatureComingSoonCard } from "@/components/admin/FeatureComingSoonCard";
import { useCampus } from "@/components/providers/CampusProvider";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  CampusApiError,
  getAdminApplications,
  getAdminUsers,
} from "@/lib/api/campus";
import { ProgramApiError, getPrograms } from "@/lib/api/programs";

interface Overview {
  users: number;
  applications: number;
  programs: number;
}

function loadedCount(value: number) {
  return value === 200 ? "200+" : String(value);
}

export default function AdminDashboardPage() {
  const { accessToken, user } = useCampus();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    if (!accessToken) {
      throw new Error("La session administrateur est absente. Reconnectez-vous.");
    }

    const [users, applications, programs] = await Promise.all([
      getAdminUsers(accessToken),
      getAdminApplications(accessToken),
      getPrograms({ include_inactive: true, limit: 200 }, accessToken),
    ]);
    return {
      users: users.length,
      applications: applications.length,
      programs: programs.length,
    };
  }, [accessToken]);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setOverview(await fetchOverview());
    } catch (requestError) {
      const message =
        requestError instanceof CampusApiError ||
        requestError instanceof ProgramApiError ||
        requestError instanceof Error
          ? requestError.message
          : "Impossible de charger les données administrateur.";
      setError(message);
      setOverview(null);
    } finally {
      setLoading(false);
    }
  }, [fetchOverview]);

  useEffect(() => {
    let active = true;
    void Promise.resolve()
      .then(fetchOverview)
      .then((result) => {
        if (active) setOverview(result);
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        const message =
          requestError instanceof CampusApiError ||
          requestError instanceof ProgramApiError ||
          requestError instanceof Error
            ? requestError.message
            : "Impossible de charger les données administrateur.";
        setError(message);
        setOverview(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fetchOverview]);

  return (
    <div className="animate-fade-in">
      <AdminPageHeader
        title={`Bonjour${user?.full_name ? `, ${user.full_name}` : ""}`}
        description="Vue d’ensemble fondée uniquement sur les données retournées par le Backend."
        icon={ClipboardList}
      />

      {error && (
        <div className="mb-6">
          <Alert variant="error" title="Chargement impossible">
            <p>{error}</p>
            <Button className="mt-3" size="sm" onClick={() => void loadOverview()}>
              Réessayer
            </Button>
          </Alert>
        </div>
      )}

      <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {[
          {
            label: "Comptes utilisateurs",
            value: overview ? loadedCount(overview.users) : null,
            href: "/admin/utilisateurs",
            icon: Users,
          },
          {
            label: "Candidatures chargées",
            value: overview ? loadedCount(overview.applications) : null,
            href: "/admin/candidatures",
            icon: ClipboardList,
          },
          {
            label: "Formations chargées",
            value: overview ? loadedCount(overview.programs) : null,
            href: "/admin/programmes",
            icon: BookOpen,
          },
        ].map(({ label, value, href, icon: Icon }) => (
          <Link
            key={label}
            href={href}
            className="rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500"
          >
            <Card hoverable accentTop>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-text-muted">{label}</p>
                  <p className="mt-2 text-3xl font-bold text-navy-800">
                    {loading ? (
                      <span className="inline-block h-9 w-16 animate-pulse rounded bg-navy-50" />
                    ) : value ?? "—"}
                  </p>
                  <p className="mt-2 text-xs text-text-muted">
                    {value === "200+" ? "Au moins 200 résultats (limite API)." : "Données chargées depuis l’API."}
                  </p>
                </div>
                <span className="rounded-lg bg-turquoise-50 p-2 text-turquoise-700">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      <Card className="mb-8">
        <h2 className="text-lg font-bold text-navy-800">Accès rapide</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {[
            ["Gérer les utilisateurs", "/admin/utilisateurs"],
            ["Examiner les candidatures", "/admin/candidatures"],
            ["Gérer le catalogue", "/admin/programmes"],
          ].map(([label, href]) => (
            <Link
              key={href}
              href={href}
              className="flex min-h-12 items-center justify-between rounded-lg border border-border px-4 py-3 text-sm font-semibold text-navy-800 transition-colors hover:border-turquoise-300 hover:bg-turquoise-50"
            >
              {label}
              <ArrowRight className="h-4 w-4 text-turquoise-700" aria-hidden="true" />
            </Link>
          ))}
        </div>
        <p className="mt-4 text-xs leading-5 text-text-muted">
          Les listes affichent jusqu’aux 200 enregistrements les plus récents, conformément à la limite du Backend.
        </p>
      </Card>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-navy-800">Espaces internes en préparation</h2>
          <p className="mt-1 text-sm text-text-muted">
            Les rôles et APIs correspondants ne sont pas déclarés dans le Backend actuel.
          </p>
        </div>
        <Badge variant="warning">Aucun indicateur simulé</Badge>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <FeatureComingSoonCard
          title="Responsable académique IIT / ISB"
          description="Dossiers, recommandations, résultats de QCM et indicateurs académiques en attente des rôles et APIs dédiés."
        />
        <FeatureComingSoonCard
          title="Responsable entretien"
          description="Candidats prêts pour entretien, rendez-vous et observations en attente des APIs métier."
        />
        <FeatureComingSoonCard
          title="Direction"
          description="Indicateurs de conversion, comparaisons IIT / ISB et formations demandées indisponibles sans APIs analytiques."
        />
      </div>
    </div>
  );
}
