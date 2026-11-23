import { notFound } from "next/navigation";
import { BarChart3, GraduationCap, MessageSquareText } from "lucide-react";
import { FeatureComingSoonCard } from "@/components/admin/FeatureComingSoonCard";
import { AdminPageHeader } from "@/components/admin/AdminPageHeader";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

const spaceDetails = {
  "academique-iit": {
    title: "Espace académique IIT",
    institution: "IIT",
    icon: GraduationCap,
    description:
      "Aperçu de l’espace réservé au responsable académique IIT.",
    sections: [
      ["Liste des candidats", "La liste dédiée à l’établissement nécessite une API académique IIT."],
      ["Détails des candidats", "Les dossiers individuels ne sont pas disponibles pour ce rôle."],
      ["Recommandations", "Aucune API de recommandation n’est déclarée dans le Backend."],
      ["Résultats des QCM", "Les évaluations et résultats ne sont pas exposés par une API."],
      ["Formations IIT", "Les données académiques détaillées pour ce rôle sont en attente."],
      ["Statistiques IIT", "Aucun indicateur académique IIT n’est disponible actuellement."],
    ],
  },
  "academique-isb": {
    title: "Espace académique ISB",
    institution: "ISB",
    icon: GraduationCap,
    description:
      "Aperçu de l’espace réservé au responsable académique ISB.",
    sections: [
      ["Liste des candidats", "La liste dédiée à l’établissement nécessite une API académique ISB."],
      ["Détails des candidats", "Les dossiers individuels ne sont pas disponibles pour ce rôle."],
      ["Recommandations", "Aucune API de recommandation n’est déclarée dans le Backend."],
      ["Résultats des QCM", "Les évaluations et résultats ne sont pas exposés par une API."],
      ["Formations ISB", "Les données académiques détaillées pour ce rôle sont en attente."],
      ["Statistiques ISB", "Aucun indicateur académique ISB n’est disponible actuellement."],
    ],
  },
  entretien: {
    title: "Espace entretien",
    institution: null,
    icon: MessageSquareText,
    description: "Aperçu de l’espace réservé au responsable entretien.",
    sections: [
      ["Candidats prêts pour entretien", "Aucune API ne définit les candidats prêts pour entretien."],
      ["Dossier candidat", "Les dossiers dédiés au rôle entretien ne sont pas accessibles."],
      ["Synthèse conversationnelle", "Aucune API de synthèse conversationnelle n’est disponible."],
      ["Gestion des rendez-vous", "Les APIs de rendez-vous ne sont pas encore disponibles."],
      ["Résultats et observations", "Aucune API ne permet d’enregistrer ou consulter ces informations."],
    ],
  },
  direction: {
    title: "Espace direction",
    institution: null,
    icon: BarChart3,
    description: "Aperçu du tableau de bord destiné à la direction.",
    sections: [
      ["Indicateurs de conversion", "Aucune API analytique ne fournit ces indicateurs."],
      ["Comparaison IIT / ISB", "Les données comparatives ne sont pas disponibles."],
      ["Formations les plus demandées", "Aucune API ne mesure actuellement la demande par formation."],
      ["Dossiers en attente", "Aucune API de synthèse direction n’est exposée."],
    ],
  },
} as const;

export default async function InternalSpacePreviewPage({
  params,
}: {
  params: Promise<{ space: string }>;
}) {
  const { space } = await params;
  const details = spaceDetails[space as keyof typeof spaceDetails];
  if (!details) notFound();

  const Icon = details.icon;

  return (
    <div className="animate-fade-in">
      <AdminPageHeader
        title={details.title}
        description={details.description}
        icon={Icon}
      />
      <Alert variant="warning" title="Fonctionnalité à venir" className="mb-6">
        <p>
          Le Backend actuel ne déclare que les rôles <strong>admin</strong> et{" "}
          <strong>candidat</strong>. Cette page est un aperçu uniquement : elle
          n’utilise aucune API administrateur pour afficher les données d’un
          futur rôle.
        </p>
      </Alert>

      <Card className="mb-6 flex flex-wrap items-center justify-between gap-4 bg-navy-800 text-white">
        <div>
          <p className="text-sm text-navy-200">Périmètre prévu</p>
          <p className="mt-1 text-lg font-bold">
            {details.institution
              ? `Établissement ${details.institution} uniquement`
              : "Espace métier dédié"}
          </p>
        </div>
        {details.institution && (
          <Badge variant={details.institution === "IIT" ? "primary" : "secondary"}>
            {details.institution}
          </Badge>
        )}
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {details.sections.map(([title, description]) => (
          <FeatureComingSoonCard
            key={title}
            title={title}
            description={description}
          />
        ))}
      </div>
    </div>
  );
}
