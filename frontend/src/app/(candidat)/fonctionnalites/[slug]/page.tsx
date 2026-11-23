import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { CandidatePageHeader } from "@/components/candidate/CandidatePageHeader";
import { FeatureComingSoon } from "@/components/candidate/FeatureComingSoon";

const features = {
  orientation: {
    title: "Orientation personnalisée",
    description:
      "Le parcours d’orientation personnalisée sera proposé lorsqu’une API dédiée sera disponible. Aucune recommandation n’est générée pour le moment.",
  },
  qcm: {
    title: "QCM d’orientation",
    description:
      "Les questionnaires ne sont pas encore disponibles. Aucun résultat ni profil d’orientation n’est simulé.",
  },
  "rendez-vous": {
    title: "Rendez-vous",
    description:
      "La prise de rendez-vous sera activée lorsqu’un service correspondant sera disponible.",
  },
  notifications: {
    title: "Notifications",
    description:
      "Aucune API de notifications n’est disponible pour le moment. Aucun événement ou message n’est inventé.",
  },
} as const;

export default async function CandidateUpcomingFeaturePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!Object.prototype.hasOwnProperty.call(features, slug)) notFound();
  const feature = features[slug as keyof typeof features];

  return (
    <div>
      <Link
        href="/dashboard"
        className="mb-6 inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-turquoise-700 hover:text-turquoise-800"
      >
        <ArrowLeft className="h-4 w-4" />
        Retour au tableau de bord
      </Link>
      <CandidatePageHeader title={feature.title} description={feature.description} />
      <FeatureComingSoon
        title={feature.title}
        description="Cette rubrique sera activée lorsqu’une API correspondante sera disponible."
      />
    </div>
  );
}
