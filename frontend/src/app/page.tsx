import Link from "next/link";
import { Suspense } from "react";
import {
  ArrowRight,
  BookOpen,
  Building2,
  CheckCircle2,
  GraduationCap,
  Search,
  Wallet,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Footer } from "@/components/layout/Footer";
import { Navbar } from "@/components/layout/Navbar";

const institutions = [
  {
    name: "Institut International de Technologie",
    acronym: "IIT",
    description:
      "Explorez les parcours de l’IIT et comparez les formations selon leur niveau et leur durée.",
    className: "bg-navy-800",
    href: "/programmes?institution=IIT",
  },
  {
    name: "Institut Supérieur de Business",
    acronym: "ISB",
    description:
      "Découvrez les formations de l’ISB et consultez les informations disponibles pour chaque parcours.",
    className: "bg-turquoise-600",
    href: "/programmes?institution=ISB",
  },
];

const features = [
  {
    icon: Search,
    title: "Un catalogue à explorer",
    description:
      "Recherchez une formation et filtrez le catalogue par établissement ou par niveau.",
  },
  {
    icon: CheckCircle2,
    title: "Les admissions en détail",
    description:
      "Consultez les conditions et les prérequis communiqués pour chaque formation.",
  },
  {
    icon: Wallet,
    title: "Une vision claire des tarifs",
    description:
      "Retrouvez les frais et les modalités de paiement lorsqu’ils sont renseignés.",
  },
];

export default function HomePage() {
  return (
    <>
      <Suspense
        fallback={
          <div
            aria-hidden="true"
            className="h-16 border-b border-border bg-white"
          />
        }
      >
        <Navbar transparent />
      </Suspense>
      <main>
        <section className="relative overflow-hidden bg-navy-800 text-white">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 overflow-hidden"
          >
            <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-turquoise-500/10 blur-3xl" />
            <div className="absolute -bottom-32 -left-16 h-80 w-80 rounded-full bg-navy-600/40 blur-3xl" />
          </div>
          <div className="container-page relative z-10 py-20 sm:py-28 lg:py-32">
            <div className="max-w-3xl">
              <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-turquoise-500/30 bg-turquoise-500/20 px-3 py-1.5 text-xs font-semibold tracking-wide text-turquoise-300">
                <GraduationCap className="h-4 w-4" />
                Orientation universitaire — IIT &amp; ISB
              </span>
              <h1 className="mb-6 text-4xl font-bold leading-tight tracking-tight text-white sm:text-5xl lg:text-6xl">
                Trouvez la formation qui{" "}
                <span className="text-turquoise-400">vous correspond.</span>
              </h1>
              <p className="mb-9 max-w-2xl text-lg leading-relaxed text-navy-200">
                SmartCampus AI vous aide à explorer les formations de l’IIT et
                de l’ISB, à comparer leurs caractéristiques et à consulter les
                informations d’admission et de tarifs disponibles.
              </p>
              <div className="flex flex-col gap-3 sm:flex-row">
                <Link href="/chat">
                  <Button
                    variant="secondary"
                    size="lg"
                    rightIcon={<ArrowRight className="h-5 w-5" />}
                  >
                    Commencer mon orientation
                  </Button>
                </Link>
                <Link
                  href="#institutions"
                  className="inline-flex h-12 items-center justify-center rounded-xl border border-white/30 px-6 text-base font-semibold text-white transition-colors hover:border-white/50 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-400"
                >
                  Découvrir les établissements
                </Link>
              </div>
            </div>
          </div>
          <div
            aria-hidden="true"
            className="absolute bottom-0 left-0 right-0 h-12 bg-bg"
            style={{ clipPath: "ellipse(60% 100% at 50% 100%)" }}
          />
        </section>

        <section id="institutions" className="section-padding bg-white">
          <div className="container-page">
            <div className="mx-auto mb-12 max-w-2xl text-center">
              <Badge variant="secondary" className="mb-4">
                Nos établissements
              </Badge>
              <h2 className="mb-4 text-3xl font-bold text-navy-800 sm:text-4xl">
                Deux établissements, plusieurs parcours
              </h2>
              <p className="leading-relaxed text-text-muted">
                Parcourez les formations de l’IIT et de l’ISB et consultez les
                informations propres à chaque programme.
              </p>
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              {institutions.map((institution) => (
                <Card
                  key={institution.acronym}
                  className="overflow-hidden p-0"
                >
                  <div className={`${institution.className} p-6 text-white sm:p-8`}>
                    <span className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-white/15">
                      <Building2 className="h-6 w-6" />
                    </span>
                    <p className="text-sm font-bold tracking-widest text-white/75">
                      {institution.acronym}
                    </p>
                    <h3 className="mt-2 text-xl font-bold text-white sm:text-2xl">
                      {institution.name}
                    </h3>
                  </div>
                  <div className="p-6 sm:p-8">
                    <p className="mb-5 leading-relaxed text-text-muted">
                      {institution.description}
                    </p>
                    <Link
                      href={institution.href}
                      className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-turquoise-700 hover:text-turquoise-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500"
                    >
                      Voir les formations {institution.acronym}
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="section-padding bg-bg">
          <div className="container-page">
            <div className="mx-auto mb-12 max-w-2xl text-center">
              <Badge variant="secondary" className="mb-4">
                Votre orientation, en toute clarté
              </Badge>
              <h2 className="mb-4 text-3xl font-bold text-navy-800 sm:text-4xl">
                Les informations essentielles, au même endroit
              </h2>
              <p className="leading-relaxed text-text-muted">
                Consultez les données publiées dans le catalogue pour comparer
                les formations en fonction de votre projet.
              </p>
            </div>
            <div className="grid gap-5 md:grid-cols-3">
              {features.map(({ icon: Icon, title, description }) => (
                <Card key={title} className="h-full">
                  <span className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-turquoise-50 text-turquoise-700">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="mb-2 text-lg font-bold text-navy-800">
                    {title}
                  </h3>
                  <p className="text-sm leading-relaxed text-text-muted">
                    {description}
                  </p>
                </Card>
              ))}
            </div>
            <div className="mt-9 text-center">
              <Link href="/programmes">
                <Button
                  variant="primary"
                  size="lg"
                  rightIcon={<BookOpen className="h-5 w-5" />}
                >
                  Explorer le catalogue
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
