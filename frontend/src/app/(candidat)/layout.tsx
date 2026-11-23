"use client";

import React, { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Menu } from "lucide-react";
import { Alert } from "@/components/ui/Alert";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar, SidebarOverlay, candidatSections } from "@/components/layout/Sidebar";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { useCampus } from "@/components/providers/CampusProvider";

/** Espace candidat protégé après vérification du profil réel du Backend. */
export default function CandidatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const { ready, startupError, user } = useCampus();
  const router = useRouter();

  React.useEffect(() => {
    if (ready && !startupError && user?.role !== "candidat") {
      const returnTo = window.location.pathname;
      router.replace(`/login?returnTo=${encodeURIComponent(returnTo)}`);
    }
  }, [ready, router, startupError, user]);

  if (!ready) {
    return <FullPageSpinner label="Vérification de votre compte candidat..." />;
  }

  if (startupError) {
    return (
      <main className="container-page flex min-h-screen items-center justify-center py-10">
        <div className="w-full max-w-xl">
          <Alert variant="error" title="Espace candidat indisponible">
            {startupError}
          </Alert>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="min-h-10 rounded-lg bg-navy-800 px-4 text-sm font-semibold text-white hover:bg-navy-700"
            >
              Réessayer
            </button>
            <Link
              href="/"
              className="inline-flex min-h-10 items-center rounded-lg px-4 text-sm font-semibold text-navy-700 hover:bg-navy-50"
            >
              Retour à l’accueil
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (!user || user.role !== "candidat") {
    return <FullPageSpinner label="Redirection vers la connexion..." />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-bg">
      {/* Navbar top (mobile : avec bouton hamburger sidebar) */}
      <Suspense
        fallback={
          <div
            aria-hidden="true"
            className="h-16 border-b border-border bg-white"
          />
        }
      >
        <Navbar />
      </Suspense>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Desktop */}
        <div className="hidden lg:flex shrink-0">
          <Sidebar sections={candidatSections} user={user} />
        </div>

        {/* Sidebar Mobile Overlay */}
        <SidebarOverlay
          open={mobileSidebarOpen}
          onClose={() => setMobileSidebarOpen(false)}
          sections={candidatSections}
          user={user}
        />

        {/* Contenu principal */}
        <main className="flex-1 overflow-y-auto">
          {/* Topbar mobile avec bouton sidebar */}
          <div className="lg:hidden flex items-center gap-3 px-4 py-3 bg-white border-b border-border">
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="p-2 rounded-lg text-navy-700 hover:bg-navy-50 transition-colors"
              aria-label="Ouvrir la navigation"
            >
              <Menu className="w-5 h-5" />
            </button>
            <span className="text-sm font-semibold text-navy-800">Mon espace</span>
          </div>

          <div className="container-page py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
