import React from "react";
import Link from "next/link";

/**
 * Layout Auth — Centré, minimaliste, sans Navbar/Footer.
 * Utilisé par /login et /register.
 */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-bg">

      {/* En-tête minimal */}
      <header className="py-6 px-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2.5 group"
          aria-label="SmartCampus AI — Retour à l'accueil"
        >
          <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-turquoise-500 text-white shadow-sm group-hover:bg-turquoise-600 transition-colors">
            <svg
              className="w-5 h-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
              <path d="M6 12v5c3 3 9 3 12 0v-5" />
            </svg>
          </span>
          <span className="flex flex-col leading-tight">
            <span className="text-base font-bold text-navy-800 tracking-tight">
              SmartCampus
            </span>
            <span className="text-[10px] font-semibold text-turquoise-500 tracking-widest uppercase -mt-0.5">
              AI
            </span>
          </span>
        </Link>
      </header>

      {/* Contenu centré */}
      <main className="flex-1 flex items-center justify-center px-4 py-8">
        {children}
      </main>

      {/* Pied de page minimal */}
      <footer className="py-4 text-center">
        <p className="text-xs text-text-muted">
          © 2026 SmartCampus AI — Tous droits réservés.
        </p>
      </footer>
    </div>
  );
}
