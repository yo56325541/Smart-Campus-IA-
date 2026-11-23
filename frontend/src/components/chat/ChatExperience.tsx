"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowUpRight,
  Clock3,
  LockKeyhole,
  MessageSquare,
  Plus,
  Send,
  UserRound,
} from "lucide-react";
import { useCampus } from "@/components/providers/CampusProvider";
import {
  CampusApiError,
  createConversation,
  getConversation,
  getConversations,
} from "@/lib/api/campus";
import type { ConversationOut } from "@/lib/types";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { CenteredSpinner } from "@/components/ui/Spinner";

const PAGE_SIZE = 50;

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return "Une erreur inattendue est survenue. Réessayez.";
}

function formatConversationDate(value: string) {
  return value.slice(0, 10);
}

export default function ChatExperience() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const conversationId = searchParams.get("conversation");
  const {
    ready,
    startupError,
    sessionToken,
    sessionInfo,
    accessToken,
    user,
    sessionConflict,
    ensureSession,
  } = useCampus();

  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [listScope, setListScope] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [activeConversation, setActiveConversation] =
    useState<ConversationOut | null>(null);
  const [activeDetailKey, setActiveDetailKey] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailErrorKey, setDetailErrorKey] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const returnTo = useMemo(
    () =>
      conversationId
        ? `/chat?conversation=${encodeURIComponent(conversationId)}`
        : "/chat",
    [conversationId],
  );
  const loginHref = `/login?returnTo=${encodeURIComponent(returnTo)}`;
  const registerHref = `/register?returnTo=${encodeURIComponent(returnTo)}`;

  const signInRequired = Boolean(sessionInfo?.linked && !user);
  const isSessionBlocked = signInRequired || sessionConflict;
  const conversationScope = user
    ? `user:${user.id}`
    : sessionToken
      ? `session:${sessionToken}`
      : null;
  const listQueryKey = `${conversationScope ?? ""}:${Boolean(accessToken)}`;
  const displayedConversations = !isSessionBlocked && listScope === listQueryKey
    ? conversations
    : [];
  const displayedActiveConversation =
    !isSessionBlocked &&
    activeDetailKey === `${conversationScope}:${conversationId}` &&
    activeConversation?.id === conversationId
      ? activeConversation
      : null;
  const displayedDetailError =
    conversationId &&
    !isSessionBlocked &&
    detailErrorKey === `${conversationScope}:${conversationId}`
      ? detailError
      : null;
  const displayedDetailLoading =
    Boolean(conversationId) &&
    !isSessionBlocked &&
    !displayedActiveConversation &&
    !displayedDetailError &&
    ready &&
    Boolean(sessionToken);
  const displayedListLoading =
    !isSessionBlocked &&
    (!ready ||
      (Boolean(sessionToken) &&
        listScope !== listQueryKey));
  const displayedListError =
    !isSessionBlocked && listScope === listQueryKey ? listError : null;

  useEffect(() => {
    if (!ready || !sessionToken || isSessionBlocked) return;

    const requestScope = listQueryKey;
    let active = true;

    getConversations(sessionToken, accessToken ?? undefined, 0, PAGE_SIZE)
      .then((result) => {
        if (!active) return;
        setConversations(result);
        setListScope(requestScope);
        setListError(null);
        setHasMore(result.length === PAGE_SIZE);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setListScope(requestScope);
        setListError(getErrorMessage(error));
        setHasMore(false);
      });

    return () => {
      active = false;
    };
  }, [
    accessToken,
    isSessionBlocked,
    listQueryKey,
    ready,
    sessionToken,
  ]);

  useEffect(() => {
    if (!conversationId || !ready || !sessionToken || isSessionBlocked) return;

    const requestKey = `${conversationScope}:${conversationId}`;
    let active = true;

    getConversation(conversationId, sessionToken, accessToken ?? undefined)
      .then((conversation) => {
        if (!active) return;
        setActiveConversation(conversation);
        setActiveDetailKey(requestKey);
        setDetailError(null);
        setDetailErrorKey(null);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setActiveConversation(null);
        setActiveDetailKey(null);
        setDetailErrorKey(requestKey);
        setDetailError(
          error instanceof CampusApiError && error.status === 404
            ? "Cette conversation n’est pas accessible avec le compte actuel."
            : getErrorMessage(error),
        );
      });
    return () => {
      active = false;
    };
  }, [
    accessToken,
    conversationScope,
    conversationId,
    isSessionBlocked,
    ready,
    sessionToken,
  ]);

  const handleCreateConversation = useCallback(async () => {
    setCreating(true);
    setCreateError(null);
    try {
      const token = await ensureSession();
      const conversation = await createConversation(
        "Nouvelle conversation",
        token,
        accessToken ?? undefined,
      );
      setConversations((current) => [
        conversation,
        ...current.filter((item) => item.id !== conversation.id),
      ]);
      const ownerScope = user ? `user:${user.id}` : `session:${token}`;
      setListScope(`${ownerScope}:${Boolean(accessToken)}`);
      router.push(`/chat?conversation=${encodeURIComponent(conversation.id)}`);
    } catch (error) {
      setCreateError(getErrorMessage(error));
    } finally {
      setCreating(false);
    }
  }, [accessToken, ensureSession, router, user]);

  async function handleLoadMore() {
    if (
      !sessionToken ||
      loadingMore ||
      !hasMore ||
      isSessionBlocked ||
      listScope !== listQueryKey
    ) return;

    setLoadingMore(true);
    setListError(null);
    try {
      const result = await getConversations(
        sessionToken,
        accessToken ?? undefined,
        displayedConversations.length,
        PAGE_SIZE,
      );
      setConversations((current) => {
        const knownIds = new Set(current.map((item) => item.id));
        return [...current, ...result.filter((item) => !knownIds.has(item.id))];
      });
      setHasMore(result.length === PAGE_SIZE);
    } catch (error) {
      setListError(getErrorMessage(error));
    } finally {
      setLoadingMore(false);
    }
  }

  const canCreate =
    ready && !isSessionBlocked;

  return (
    <div className="container-page py-8 sm:py-10">
      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-turquoise-700">
            SmartCampus AI
          </p>
          <h1 className="text-3xl font-bold text-navy-800">
            Votre espace de conversation
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-muted">
            Démarrez une session visiteur et retrouvez les conversations
            enregistrées par le service.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 self-start rounded-full border border-border bg-white px-3 py-2 text-sm text-navy-700 sm:self-auto">
          {user ? (
            <>
              <UserRound className="h-4 w-4 text-turquoise-700" />
              <span className="max-w-48 truncate">
                {user.full_name || user.email}
              </span>
            </>
          ) : (
            <>
              <LockKeyhole className="h-4 w-4 text-turquoise-700" />
              <span>Visiteur</span>
            </>
          )}
        </div>
      </header>

      {startupError && (
        <Alert
          variant="error"
          title="La session n’a pas pu être préparée"
          className="mb-6"
        >
          <p>{startupError}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-3 font-semibold underline underline-offset-2"
          >
            Réessayer
          </button>
        </Alert>
      )}

      {sessionConflict && (
        <Alert
          variant="warning"
          title="Cette session appartient déjà à un autre compte"
          className="mb-6"
        >
          La conversation n’a pas été transférée à ce compte. Déconnectez-vous
          puis connectez-vous au compte auquel la session a été rattachée. Aucun
          historique local ne peut remplacer les données du Backend.
        </Alert>
      )}

      {signInRequired && !sessionConflict && (
        <Alert
          variant="info"
          title="Votre session est rattachée à un compte"
          className="mb-6"
        >
          Connectez-vous avec le compte associé pour retrouver vos conversations.
          <div className="mt-3 flex flex-wrap gap-3">
            <Link
              href={loginHref}
              className="inline-flex min-h-10 items-center rounded-lg bg-navy-800 px-4 text-sm font-semibold text-white hover:bg-navy-700"
            >
              Se connecter
            </Link>
            <Link
              href={registerHref}
              className="inline-flex min-h-10 items-center rounded-lg border border-navy-300 px-4 text-sm font-semibold text-navy-800 hover:bg-navy-50"
            >
              Créer un compte
            </Link>
          </div>
        </Alert>
      )}

      <Alert
        variant="warning"
        title="Envoi de messages IA indisponible"
        className="mb-6"
      >
        Le Backend ne propose pas encore d’API d’envoi de messages au LLM.
        Vous pouvez créer et retrouver vos conversations, mais aucun message
        ni aucune réponse intelligente ne seront simulés.
      </Alert>

      <div className="grid gap-5 lg:grid-cols-[minmax(17rem,0.8fr)_minmax(0,1.7fr)]">
        <Card className="flex min-h-80 flex-col p-0">
          <div className="flex items-center justify-between gap-3 border-b border-border p-5">
            <div className="min-w-0">
              <h2 className="font-bold text-navy-800">Conversations</h2>
              <p className="mt-1 text-xs text-text-muted">
                Historique fourni par le Backend
              </p>
            </div>
            <Button
              size="icon"
              variant="secondary"
              aria-label="Créer une conversation"
              title="Créer une conversation"
              disabled={!canCreate || creating}
              loading={creating}
              onClick={handleCreateConversation}
            >
              {!creating && <Plus className="h-5 w-5" />}
            </Button>
          </div>

          <div className="flex-1 p-3">
            {isSessionBlocked ? (
              <p className="px-3 py-6 text-center text-sm text-text-muted">
                Connectez-vous pour charger les conversations rattachées à
                votre compte.
              </p>
            ) : displayedListLoading ? (
              <CenteredSpinner
                label="Chargement des conversations..."
                className="py-10"
              />
            ) : displayedListError ? (
              <div className="p-3" role="alert">
                <p className="text-sm leading-relaxed text-red-700">
                  {displayedListError}
                </p>
                <button
                  type="button"
                  onClick={() => window.location.reload()}
                  className="mt-2 text-sm font-semibold text-navy-800 underline"
                >
                  Recharger
                </button>
              </div>
            ) : displayedConversations.length === 0 ? (
              <div className="px-3 py-8 text-center">
                <MessageSquare className="mx-auto mb-3 h-7 w-7 text-navy-300" />
                <p className="text-sm font-semibold text-navy-800">
                  Aucune conversation enregistrée
                </p>
                <p className="mt-1 text-xs leading-relaxed text-text-muted">
                  Créez une conversation pour qu’elle soit conservée par le
                  Backend.
                </p>
              </div>
            ) : (
              <ul className="flex max-h-[28rem] flex-col gap-1 overflow-y-auto">
                {displayedConversations.map((conversation) => {
                  const selected = conversation.id === conversationId;
                  return (
                    <li key={conversation.id}>
                      <button
                        type="button"
                        aria-current={selected ? "page" : undefined}
                        onClick={() =>
                          router.push(
                            `/chat?conversation=${encodeURIComponent(conversation.id)}`,
                          )
                        }
                        className={`w-full rounded-lg px-3 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500 ${
                          selected
                            ? "bg-turquoise-50 text-turquoise-900"
                            : "text-navy-800 hover:bg-navy-50"
                        }`}
                      >
                        <span className="block truncate text-sm font-semibold">
                          {conversation.title || "Conversation sans titre"}
                        </span>
                        <span className="mt-1 inline-flex items-center gap-1.5 text-xs text-text-muted">
                          <Clock3 className="h-3.5 w-3.5" />
                          {formatConversationDate(conversation.created_at)}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {hasMore &&
            !displayedListLoading &&
            !isSessionBlocked &&
                listScope === listQueryKey && (
            <div className="border-t border-border p-3">
              <Button
                variant="ghost"
                fullWidth
                loading={loadingMore}
                onClick={handleLoadMore}
              >
                Charger plus
              </Button>
            </div>
          )}
        </Card>

        <Card className="flex min-h-[26rem] flex-col overflow-hidden p-0">
          <div className="flex items-center gap-3 border-b border-border px-5 py-4 sm:px-6">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-800 text-white">
              <MessageSquare className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="truncate font-bold text-navy-800">
                {displayedActiveConversation?.title || "Nouvelle conversation"}
              </h2>
              <p className="text-xs text-text-muted">
                {displayedActiveConversation
                  ? `Créée le ${formatConversationDate(displayedActiveConversation.created_at)}`
                  : "Conversation visiteur"}
              </p>
            </div>
            {displayedActiveConversation && (
              <span className="rounded-full bg-turquoise-50 px-2.5 py-1 text-xs font-semibold text-turquoise-800">
                Enregistrée
              </span>
            )}
          </div>

          <div className="flex flex-1 flex-col items-center justify-center p-6 text-center sm:p-10">
            {displayedDetailLoading ? (
              <CenteredSpinner
                label="Récupération de la conversation..."
                className="py-8"
              />
            ) : displayedDetailError ? (
              <div className="max-w-md" role="alert">
                <AlertCircle className="mx-auto mb-3 h-8 w-8 text-amber-500" />
                <p className="text-sm leading-relaxed text-text-muted">
                  {displayedDetailError}
                </p>
              </div>
            ) : displayedActiveConversation ? (
              <div className="max-w-md">
                <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-navy-50 text-navy-600">
                  <MessageSquare className="h-7 w-7" />
                </span>
                <h3 className="mb-2 text-lg font-bold text-navy-800">
                  Conversation retrouvée
                </h3>
                <p className="text-sm leading-relaxed text-text-muted">
                  Le Backend confirme que cette conversation est accessible.
                  Les APIs disponibles renvoient ses informations, mais pas le
                  contenu des messages.
                </p>
              </div>
            ) : (
              <div className="max-w-md">
                <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-turquoise-50 text-turquoise-700">
                  <MessageSquare className="h-7 w-7" />
                </span>
                <h3 className="mb-2 text-lg font-bold text-navy-800">
                  {conversationId
                    ? "Conversation non disponible"
                    : "Votre espace est prêt"}
                </h3>
                <p className="text-sm leading-relaxed text-text-muted">
                  {conversationId
                    ? "Sélectionnez une conversation accessible depuis cette session ou créez-en une nouvelle."
                    : "Créez une conversation ou sélectionnez un élément de l’historique pour consulter les informations disponibles."}
                </p>
                {!conversationId && (
                  <Button
                    className="mt-5"
                    variant="secondary"
                    leftIcon={<Plus className="h-4 w-4" />}
                    disabled={!canCreate || creating}
                    loading={creating}
                    onClick={handleCreateConversation}
                  >
                    Créer une conversation
                  </Button>
                )}
              </div>
            )}
          </div>

          {createError && (
            <div className="px-5 pb-3 sm:px-6" role="alert">
              <p className="text-sm text-red-700">{createError}</p>
            </div>
          )}

          <div className="border-t border-border bg-bg/70 p-4 sm:p-5">
            <div className="flex gap-3">
              <textarea
                aria-label="Message"
                disabled
                placeholder="L’envoi de messages IA n’est pas encore disponible."
                rows={2}
                className="min-h-12 flex-1 resize-none rounded-lg border border-border bg-slate-50 px-4 py-3 text-sm text-text-muted placeholder:text-text-subtle"
              />
              <Button
                size="icon"
                aria-label="Envoyer un message"
                title="L’envoi de messages IA n’est pas encore disponible"
                disabled
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <p className="mt-2 flex items-center gap-1.5 text-xs text-text-muted">
              <ArrowUpRight className="h-3.5 w-3.5" />
              Aucun message ni réponse IA n’est généré par cette interface.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
