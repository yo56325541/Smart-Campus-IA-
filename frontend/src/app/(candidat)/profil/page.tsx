"use client";

import { Alert } from "@/components/ui/Alert";
import { CandidatePageHeader } from "@/components/candidate/CandidatePageHeader";
import { FeatureComingSoon } from "@/components/candidate/FeatureComingSoon";
import { Card } from "@/components/ui/Card";
import { useCampus } from "@/components/providers/CampusProvider";
import { formatCandidateDate } from "@/lib/candidate";

export default function CandidateProfilePage() {
  const { user } = useCampus();

  if (!user) {
    return (
      <Alert variant="error" title="Profil indisponible">
        Les informations du compte candidat n’ont pas pu être récupérées.
      </Alert>
    );
  }

  return (
    <div>
      <CandidatePageHeader
        title="Mon profil"
        description="Ces informations sont lues depuis le profil renvoyé par le Backend. Elles ne sont pas modifiables depuis cette interface."
      />

      <Card>
        <h2 className="text-lg font-bold text-navy-800">Informations du compte</h2>
        <dl className="mt-5 grid gap-5 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
              Nom complet
            </dt>
            <dd className="mt-1 break-words font-medium text-navy-800">
              {user.full_name || "Non renseigné"}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
              Adresse e-mail
            </dt>
            <dd className="mt-1 break-all font-medium text-navy-800">
              {user.email}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
              Type de compte
            </dt>
            <dd className="mt-1 font-medium capitalize text-navy-800">
              {user.role}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
              État du compte
            </dt>
            <dd className="mt-1 font-medium text-navy-800">
              {user.is_active ? "Actif" : "Inactif"}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
              Compte créé le
            </dt>
            <dd className="mt-1 font-medium text-navy-800">
              {formatCandidateDate(user.created_at)}
            </dd>
          </div>
        </dl>
      </Card>

      <div className="mt-6">
        <FeatureComingSoon
          title="Modification du profil"
          description="La modification du nom ou de l’adresse e-mail est à venir. Aucune API de mise à jour du profil n’est actuellement disponible."
        />
      </div>
    </div>
  );
}
