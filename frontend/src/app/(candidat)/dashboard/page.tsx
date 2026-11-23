"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  FileText,
  MessageSquare,
  UserRound,
} from "lucide-react";
import { Alert } from "@/components/ui/Alert";
import { CandidatePageHeader } from "@/components/candidate/CandidatePageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useCampus } from "@/components/providers/CampusProvider";
import {
  getMyApplications,
  getConversations,
} from "@/lib/api/campus";
import { getCandidateErrorMessage } from "@/lib/candidate";
import type { ApplicationOut, ConversationOut } from "@/lib/types";

function MetricCard({
  title,
  icon: Icon,
  href,
  loading,
  error,
  value,
  detail,
  onRetry,
}: {
  title: string;
  icon: typeof FileText;
  href: string;
  loading?: boolean;
  error?: string | null;
  value: string;
  detail: string;
  onRetry?: () => void;
}) {
  return (
    <Card className="flex h-full flex-col" accentTop>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-navy-700">{title}</p>
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-turquoise-50 text-turquoise-700">
          <Icon className="h-5 w-5" />
        </span>
      </div>
      <div className="mt-5 min-h-14">
        {loading ? (
          <Spinner label={`Chargement : ${title.toLocaleLowerCase("fr")}`} />
        ) : error ? (
          <div>
            <p className="text-sm text-red-700">{error}</p>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="mt-2 text-sm font-semibold text-navy-700 underline underline-offset-2"
              >
                Réessayer
              </button>
            )}
          </div>
        ) : (
          <>
            <p className="text-3xl font-bold text-navy-800">{value}</p>
            <p className="mt-1 text-sm text-text-muted">{detail}</p>
          </>
        )}
      </div>
      <Link
        href={href}
        className="mt-auto inline-flex min-h-10 items-center gap-2 pt-4 text-sm font-semibold text-turquoise-700 hover:text-turquoise-800"
      >
        Accéder
        <ArrowRight className="h-4 w-4" />
      </Link>
    </Card>
  );
}

export default function CandidatDashboardPage() {
  const { user, accessToken, sessionConflict } = useCampus();
  const [applications, setApplications] = useState<ApplicationOut[] | null>(null);
  const [applicationsError, setApplicationsError] = useState<string | null>(null);
  const [applicationsLoading, setApplicationsLoading] = useState(true);
  const [conversations, setConversations] = useState<ConversationOut[] | null>(null);
  const [conversationsError, setConversationsError] = useState<string | null>(null);
  const [conversationsLoading, setConversationsLoading] = useState(true);

  const fetchApplications = useCallback(() => {
    if (!accessToken) {
      return Promise.reject(
        new Error("La session candidat n’est pas disponible."),
      );
    }
    return getMyApplications(accessToken);
  }, [accessToken]);

  const reloadApplications = useCallback(async () => {
    if (!accessToken) return;
    setApplicationsLoading(true);
    setApplicationsError(null);
    try {
      setApplications(await fetchApplications());
    } catch (error) {
      setApplicationsError(getCandidateErrorMessage(error));
    } finally {
      setApplicationsLoading(false);
    }
  }, [accessToken, fetchApplications]);

  const fetchConversations = useCallback(async () => {
    if (!accessToken) {
      throw new Error("La session candidat n’est pas disponible.");
    }
    return getConversations(undefined, accessToken, 0, 200);
  }, [accessToken]);

  const reloadConversations = useCallback(async () => {
    if (!accessToken) return;
    setConversationsLoading(true);
    setConversationsError(null);
    try {
      setConversations(await fetchConversations());
    } catch (error) {
      setConversationsError(getCandidateErrorMessage(error));
    } finally {
      setConversationsLoading(false);
    }
  }, [accessToken, fetchConversations]);

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
    if (!accessToken) return;
    let active = true;
    void fetchConversations()
      .then((result) => {
        if (active) {
          setConversations(result);
          setConversationsError(null);
        }
      })
      .catch((error: unknown) => {
        if (active) setConversationsError(getCandidateErrorMessage(error));
      })
      .finally(() => {
        if (active) setConversationsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [accessToken, fetchConversations]);

  const applicationValue =
    applications === null
      ? "—"
      : applications.length === 200
        ? "200+"
        : String(applications.length);
  const conversationValue =
    conversations === null
      ? "—"
      : conversations.length === 200
        ? "200+"
        : String(conversations.length);

  return (
    <div className="animate-fade-in">
      <section className="mb-8 overflow-hidden rounded-2xl bg-gradient-to-br from-navy-800 to-navy-900 px-6 py-7 text-white sm:px-8 sm:py-9">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-turquoise-300">
          Tableau de bord
        </p>
        <h1 className="mt-2 text-2xl font-bold sm:text-3xl">
          Bienvenue{user?.full_name ? `, ${user.full_name}` : ""}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-navy-100 sm:text-base">
          Retrouvez ici les informations de votre compte et les démarches
          enregistrées auprès de SmartCampus AI.
        </p>
      </section>

      {sessionConflict && (
        <Alert className="mb-6" variant="warning" title="Session visiteur non rattachée">
          La session visiteur est déjà liée à un autre compte. Seules les
          conversations appartenant à votre compte candidat sont affichées.
        </Alert>
      )}

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        <MetricCard
          title="Mes candidatures"
          icon={FileText}
          href="/candidatures"
          loading={applicationsLoading}
          error={applicationsError}
          value={applicationValue}
          detail={
            applications?.length === 0
              ? "Aucune candidature enregistrée."
              : applications?.length === 200
                ? "200 dernières candidatures chargées."
                : "Candidatures retournées par le Backend."
          }
          onRetry={() => void reloadApplications()}
        />
        <MetricCard
          title="Mes conversations"
          icon={MessageSquare}
          href="/conversations"
          loading={conversationsLoading}
          error={conversationsError}
          value={conversationValue}
          detail={
            conversations?.length === 0
              ? "Aucune conversation enregistrée."
              : conversations?.length === 200
                ? "200 dernières conversations chargées."
                : "Conversations rattachées à votre compte."
          }
          onRetry={() => void reloadConversations()}
        />
        <MetricCard
          title="Mon profil"
          icon={UserRound}
          href="/profil"
          value={user?.is_active ? "Actif" : "Inactif"}
          detail={user?.email ?? "Adresse e-mail indisponible"}
        />
      </div>

      <section className="mt-8">
        <CandidatePageHeader
          eyebrow="Accès rapide"
          title="Poursuivre votre parcours"
          description="Consultez le catalogue des formations et les informations d’admission et de tarifs publiées."
        />
        <div className="grid gap-5 md:grid-cols-2">
          <Card className="flex items-start gap-4">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-navy-50 text-navy-700">
              <BookOpen className="h-5 w-5" />
            </span>
            <div>
              <h2 className="font-bold text-navy-800">Catalogue des formations</h2>
              <p className="mt-1 text-sm leading-relaxed text-text-muted">
                Les formations, conditions d’admission et tarifs sont consultables dans le catalogue.
              </p>
              <Link
                href="/programmes"
                className="mt-3 inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-turquoise-700 hover:text-turquoise-800"
              >
                Parcourir les formations
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </Card>
          <Card className="flex items-start gap-4">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-turquoise-50 text-turquoise-700">
              <FileText className="h-5 w-5" />
            </span>
            <div>
              <h2 className="font-bold text-navy-800">Suivre une candidature</h2>
              <p className="mt-1 text-sm leading-relaxed text-text-muted">
                Déposez une candidature pour une formation active et consultez son statut.
              </p>
              <Link
                href="/candidatures"
                className="mt-3 inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-turquoise-700 hover:text-turquoise-800"
              >
                Voir mes candidatures
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </Card>
        </div>
      </section>

      {user && !user.full_name && (
        <Alert className="mt-6" variant="info" title="Profil candidat">
          Votre nom n’est pas renseigné sur le profil. La modification du profil n’est pas encore proposée, car aucune API de mise à jour n’est disponible.
        </Alert>
      )}
    </div>
  );
}
