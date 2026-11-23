"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, MessageSquare } from "lucide-react";
import { Alert, ApiErrorAlert } from "@/components/ui/Alert";
import { CandidatePageHeader } from "@/components/candidate/CandidatePageHeader";
import { Card } from "@/components/ui/Card";
import { CenteredSpinner } from "@/components/ui/Spinner";
import { useCampus } from "@/components/providers/CampusProvider";
import { getConversations } from "@/lib/api/campus";
import { formatCandidateDate, getCandidateErrorMessage } from "@/lib/candidate";
import type { ConversationOut } from "@/lib/types";

export default function CandidateConversationsPage() {
  const { accessToken, sessionConflict } = useCampus();
  const [conversations, setConversations] = useState<ConversationOut[] | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConversations = useCallback(async () => {
    if (!accessToken) {
      throw new Error("La session candidat n’est pas disponible.");
    }
    return getConversations(undefined, accessToken, 0, 200);
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    void fetchConversations()
      .then((result) => {
        if (active) {
          setConversations(result);
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
  }, [accessToken, fetchConversations]);

  async function retryConversations() {
    setLoading(true);
    setError(null);
    try {
      setConversations(await fetchConversations());
    } catch (reason) {
      setError(getCandidateErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <CandidatePageHeader
        title="Mes conversations"
        description="Historique transmis par le Backend, y compris les conversations rattachées depuis votre session visiteur."
      />

      {sessionConflict && (
        <Alert className="mb-5" variant="warning" title="Session visiteur non rattachée">
          La session visiteur est déjà liée à un autre compte. Seules les
          conversations de votre compte candidat sont affichées.
        </Alert>
      )}

      {loading ? (
        <CenteredSpinner label="Chargement des conversations..." />
      ) : error ? (
        <div>
          <ApiErrorAlert message={error} />
          <button
            type="button"
            onClick={() => void retryConversations()}
            className="mt-4 min-h-10 rounded-lg bg-navy-800 px-4 text-sm font-semibold text-white hover:bg-navy-700"
          >
            Réessayer
          </button>
        </div>
      ) : conversations?.length === 0 ? (
        <Card className="py-12 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-navy-50 text-navy-700">
            <MessageSquare className="h-6 w-6" />
          </span>
          <h2 className="mt-4 text-lg font-bold text-navy-800">
            Aucune conversation enregistrée
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-text-muted">
            Les conversations visiteur apparaîtront ici si le Backend les a
            rattachées à ce compte.
          </p>
          <Link
            href="/chat"
            className="mt-5 inline-flex min-h-10 items-center justify-center rounded-lg bg-navy-800 px-4 text-sm font-semibold text-white hover:bg-navy-700"
          >
            Ouvrir l’espace de conversation
          </Link>
        </Card>
      ) : (
        <div className="space-y-3">
          {conversations?.map((conversation) => (
            <Card
              key={conversation.id}
              className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <h2 className="break-words font-semibold text-navy-800">
                  {conversation.title || "Conversation sans titre"}
                </h2>
                <p className="mt-1 text-sm text-text-muted">
                  Créée le {formatCandidateDate(conversation.created_at)}
                </p>
              </div>
              <Link
                href={`/conversations/${encodeURIComponent(conversation.id)}`}
                className="inline-flex min-h-10 shrink-0 items-center gap-2 font-semibold text-turquoise-700 hover:text-turquoise-800"
              >
                Consulter
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Card>
          ))}
          {conversations?.length === 200 && (
            <p className="text-sm text-text-muted">
              Seules les 200 conversations les plus récentes sont chargées.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
