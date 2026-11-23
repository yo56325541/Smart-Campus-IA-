"use client";

import React, { useEffect, useState } from "react";
import { LogOut, Menu } from "lucide-react";
import { useRouter } from "next/navigation";
import { Sidebar, SidebarOverlay, adminSections } from "@/components/layout/Sidebar";
import { useCampus } from "@/components/providers/CampusProvider";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { FullPageSpinner } from "@/components/ui/Spinner";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const { ready, startupError, user, logout } = useCampus();
  const router = useRouter();

  useEffect(() => {
    if (ready && !startupError && user?.role !== "admin") {
      if (user?.role === "candidat") {
        router.replace("/dashboard");
      } else {
        const returnTo = window.location.pathname + window.location.search;
        router.replace(`/login?returnTo=${encodeURIComponent(returnTo)}`);
      }
    }
  }, [ready, router, startupError, user]);

  if (!ready) return <FullPageSpinner label="Vérification des droits d’accès…" />;

  if (startupError) {
    return (
      <main className="container-page flex min-h-screen items-center justify-center py-10">
        <div className="w-full max-w-xl">
          <Alert variant="error" title="Espace administrateur indisponible">
            {startupError}
          </Alert>
          <div className="mt-5">
            <Button onClick={() => window.location.reload()}>
              Réessayer
            </Button>
          </div>
        </div>
      </main>
    );
  }

  if (user?.role !== "admin") {
    return <FullPageSpinner label="Vérification des droits d’accès…" />;
  }

  return (
    <div className="min-h-screen flex bg-bg">
      {/* Sidebar Desktop */}
      <div className="hidden lg:flex shrink-0 sticky top-0 h-screen">
        <Sidebar sections={adminSections} user={user} />
      </div>

      {/* Sidebar Mobile Overlay */}
      <SidebarOverlay
        open={mobileSidebarOpen}
        onClose={() => setMobileSidebarOpen(false)}
        sections={adminSections}
        user={user}
      />

      {/* Zone principale */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar Admin */}
        <header className="sticky top-0 z-30 bg-white border-b border-border shadow-navbar">
          <div className="flex items-center gap-4 px-6 h-16">
            {/* Burger mobile */}
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg text-navy-700 hover:bg-navy-50 transition-colors"
              aria-label="Ouvrir la navigation"
            >
              <Menu className="w-5 h-5" />
            </button>

            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-bold text-navy-800">
                Espace administrateur
              </p>
              <p className="truncate text-xs text-text-muted">
                {user.full_name || user.email} · {user.email}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="hidden rounded-full bg-turquoise-50 px-3 py-1 text-xs font-semibold text-turquoise-800 sm:inline-flex">
                Administrateur
              </span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={logout}
                leftIcon={<LogOut className="h-4 w-4" />}
              >
                <span className="hidden sm:inline">Déconnexion</span>
              </Button>
            </div>
          </div>
        </header>

        {/* Contenu page */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-6 py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
