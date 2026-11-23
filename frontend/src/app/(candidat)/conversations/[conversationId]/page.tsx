"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, MessageSquare } from "lucide-react";
import { Alert, ApiErrorAlert } from "@/components/ui/Alert";
import { CandidatePageHeader } from "@/components/candidate/CandidatePageHeader";
import { Card } from "@/components/ui/Card";
import { CenteredSpinner } from "@/components/ui/Spinner";
import { useCampus } from "@/components/providers/CampusProvider";
import { getConversation } from "@/lib/api/campus";
import {
  formatCandidateDate,
  getCandidateErrorMessage,
} from "@/lib/candidate";
import type { ConversationOut } from "@/lib/types";

export default function CandidateConversationDetailPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const { accessToken } = useCampus();
  const [conversation, setConversation] = useState<ConversationOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConversation = useCallback(async () => {
    if (!accessToken) {
      throw new Error("La session candidat n’est pas disponible.");
    }
    return getConversation(conversationId, undefined, accessToken);
  }, [accessToken, conversationId]);

  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    void fetchConversation()
      .then((result) => {
        if (active) {
          setConversation(result);
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
  }, [accessToken, fetchConversation]);

  async function retryConversation() {
    setLoading(true);
    setError(null);
    try {
      setConversation(await fetchConversation());
    } catch (reason) {
      setError(getCandidateErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <Link
        href="/conversations"
        className="mb-6 inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-turquoise-700 hover:text-turquoise-800"
      >
        <ArrowLeft className="h-4 w-4" />
        Retour aux conversations
      </Link>

      <CandidatePageHeader
        title="Détail de la conversation"
        description="Les informations affichées proviennent de la conversation retournée par le Backend."
      />

      {loading ? (
        <CenteredSpinner label="Chargement de la conversation..." />
      ) : error ? (
        <div>
          <ApiErrorAlert message={error} />
          <button
            type="button"
            onClick={() => void retryConversation()}
            className="mt-4 min-h-10 rounded-lg bg-navy-800 px-4 text-sm font-semibold text-white hover:bg-navy-700"
          >
            Réessayer
          </button>
        </div>
      ) : conversation ? (
        <div className="space-y-5">
          <Card>
            <div className="flex items-start gap-4">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-turquoise-50 text-turquoise-700">
                <MessageSquare className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <h2 className="break-words text-lg font-bold text-navy-800">
                  {conversation.title || "Conversation sans titre"}
                </h2>
                <p className="mt-2 text-sm text-text-muted">
                  Créée le {formatCandidateDate(conversation.created_at)}
                </p>
              </div>
            </div>
          </Card>
          <Alert variant="info" title="Contenu des messages indisponible">
            L’API de détail retourne les métadonnées de la conversation, mais
            aucune API ne permet actuellement de récupérer les messages.
          </Alert>
        </div>
      ) : (
        <Card>
          <p className="text-sm text-text-muted">
            Aucune donnée de conversation n’a été retournée.
          </p>
        </Card>
      )}
    </div>
  );
}
