"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Menu, X, GraduationCap, ChevronDown, User, LogOut, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { UserOut } from "@/lib/types";
import { useCampus } from "@/components/providers/CampusProvider";

// ─── Logo SmartCampus ─────────────────────────────────────────────────────────

function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2.5 group shrink-0">
      <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-turquoise-500 text-white shadow-sm group-hover:bg-turquoise-600 transition-colors">
        <GraduationCap className="w-5 h-5" />
      </span>
      {!compact && (
        <span className="flex flex-col leading-tight">
          <span className="text-base font-bold text-navy-800 tracking-tight">
            SmartCampus
          </span>
          <span className="text-[10px] font-semibold text-turquoise-500 tracking-widest uppercase -mt-0.5">
            AI
          </span>
        </span>
      )}
    </Link>
  );
}

// ─── Liens de navigation ──────────────────────────────────────────────────────

interface NavItem {
  label: string;
  href: string;
  exact?: boolean;
}

const publicNavItems: NavItem[] = [
  { label: "Accueil",     href: "/",           exact: true },
  { label: "Espace visiteur", href: "/chat" },
  { label: "Formations",  href: "/programmes" },
  { label: "IIT",         href: "/programmes?institution=IIT" },
  { label: "ISB",         href: "/programmes?institution=ISB" },
];

function NavLink({
  href,
  label,
  exact,
  onClick,
}: NavItem & { onClick?: () => void }) {
  const pathname = usePathname();
  const isActive = exact ? pathname === href : pathname.startsWith(href) && href !== "/";

  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        "relative text-sm font-medium transition-colors duration-150",
        "hover:text-turquoise-600",
        isActive ? "text-turquoise-600" : "text-navy-700"
      )}
    >
      {label}
      {isActive && (
        <span className="absolute -bottom-1 left-0 right-0 h-0.5 bg-turquoise-500 rounded-full" />
      )}
    </Link>
  );
}

// ─── Menu utilisateur connecté ────────────────────────────────────────────────

function UserMenu({
  user,
  onLogout,
}: {
  user: UserOut;
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);

  const initials = user.full_name
    ? user.full_name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase()
    : user.email[0].toUpperCase();

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-lg",
          "text-sm font-medium text-navy-800",
          "hover:bg-navy-50 transition-colors duration-150",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500"
        )}
        aria-expanded={open}
        aria-haspopup="true"
      >
        <span className="flex items-center justify-center w-7 h-7 rounded-full bg-navy-800 text-white text-xs font-bold shrink-0">
          {initials}
        </span>
        <span className="hidden sm:block max-w-28 truncate">{user.full_name || user.email}</span>
        <ChevronDown className={cn("w-3.5 h-3.5 transition-transform duration-150 text-navy-500", open && "rotate-180")} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} aria-hidden="true" />
          <div className="absolute right-0 mt-2 w-52 z-20 bg-white rounded-xl border border-border shadow-xl py-1 animate-fade-in">
            <div className="px-4 py-3 border-b border-border">
              <p className="text-xs text-text-muted">Connecté en tant que</p>
              <p className="text-sm font-semibold text-navy-800 truncate">{user.email}</p>
              <span className="text-xs font-medium text-turquoise-600 capitalize">{user.role}</span>
            </div>

            {user.role === "candidat" && (
              <Link
                href="/dashboard"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 px-4 py-2.5 text-sm text-navy-700 hover:bg-navy-50 transition-colors"
              >
                <User className="w-4 h-4" />
                Mon espace candidat
              </Link>
            )}

            <Link
              href={user.role === "candidat" ? "/conversations" : "/chat"}
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 px-4 py-2.5 text-sm text-navy-700 hover:bg-navy-50 transition-colors"
            >
              <User className="w-4 h-4" />
              {user.role === "candidat" ? "Mes conversations" : "Espace visiteur"}
            </Link>

            <button
              onClick={() => { setOpen(false); onLogout(); }}
              className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Se déconnecter
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

export interface NavbarProps {
  /** Variante transparente pour landing hero */
  transparent?: boolean;
  user?: UserOut | null;
}

// ─── Composant principal ──────────────────────────────────────────────────────

export function Navbar({ transparent = false }: NavbarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user, logout, ready } = useCampus();
  const conversationId = searchParams.get("conversation");
  const returnTo =
    pathname === "/chat" && conversationId
      ? `/chat?conversation=${encodeURIComponent(conversationId)}`
      : "/chat";
  const loginHref = `/login?returnTo=${encodeURIComponent(returnTo)}`;
  const registerHref = `/register?returnTo=${encodeURIComponent(returnTo)}`;

  // Effet de scroll pour la navbar transparente
  useEffect(() => {
    if (!transparent) return;
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, [transparent]);

  const navBg = transparent && !scrolled && !mobileOpen
    ? "bg-transparent border-transparent"
    : "bg-white/95 backdrop-blur-md border-b border-border shadow-navbar";

  return (
    <header
      className={cn(
        "sticky top-0 z-40 transition-all duration-300",
        navBg
      )}
    >
      <nav
        className="container-page h-16 flex items-center justify-between gap-4"
        aria-label="Navigation principale"
      >
        {/* Logo */}
        <Logo />

        {/* Liens Desktop */}
        <div className="hidden md:flex items-center gap-6 pb-0.5">
          {publicNavItems.map(item => (
            <NavLink key={item.href} {...item} />
          ))}
        </div>

        {/* Actions Desktop */}
        <div className="hidden md:flex items-center gap-2">
          {user ? (
            <UserMenu user={user} onLogout={logout} />
          ) : !ready ? (
            <span
              aria-hidden="true"
              className="h-10 w-32 animate-pulse rounded-lg bg-navy-50"
            />
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href={loginHref}
                className="inline-flex min-h-10 items-center rounded-lg px-3 text-sm font-semibold text-navy-700 transition-colors hover:bg-navy-50"
              >
                Connexion
              </Link>
              <Link
                href={registerHref}
                className="inline-flex min-h-10 items-center justify-center rounded-lg bg-turquoise-500 px-4 text-sm font-semibold text-white transition-colors hover:bg-turquoise-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500 focus-visible:ring-offset-2"
              >
                Créer un compte
              </Link>
            </div>
          )}
        </div>

        {/* Burger Mobile */}
        <button
          className={cn(
            "md:hidden flex items-center justify-center w-10 h-10 rounded-lg",
            "text-navy-800 hover:bg-navy-50 transition-colors",
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500"
          )}
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label={mobileOpen ? "Fermer le menu" : "Ouvrir le menu"}
          aria-expanded={mobileOpen}
          aria-controls="mobile-menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </nav>

      {/* Menu Mobile */}
      {mobileOpen && (
        <div
          id="mobile-menu"
          className="md:hidden border-t border-border bg-white animate-fade-in"
        >
          <div className="container-page py-4 flex flex-col gap-1">
            {publicNavItems.map(item => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  "hover:bg-navy-50 hover:text-turquoise-600",
                  pathname === item.href
                    ? "bg-turquoise-50 text-turquoise-700"
                    : "text-navy-700"
                )}
              >
                {item.label}
              </Link>
            ))}

            <div className="border-t border-border mt-2 pt-3 flex flex-col gap-2">
              {user ? (
                <>
                  <div className="px-3 py-2 bg-navy-50 rounded-lg">
                    <p className="text-xs text-text-muted">Connecté en tant que</p>
                    <p className="text-sm font-semibold text-navy-800">{user.full_name || user.email}</p>
                  </div>
                  {user.role === "candidat" && (
                    <>
                      <Link
                        href="/dashboard"
                        onClick={() => setMobileOpen(false)}
                        className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-navy-700 hover:bg-navy-50"
                      >
                        <User className="w-4 h-4" />
                        Mon espace candidat
                      </Link>
                      <Link
                        href="/conversations"
                        onClick={() => setMobileOpen(false)}
                        className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-navy-700 hover:bg-navy-50"
                      >
                        <MessageSquare className="w-4 h-4" />
                        Mes conversations
                      </Link>
                    </>
                  )}
                  <Link
                    href={user.role === "candidat" ? "/profil" : "/chat"}
                    onClick={() => setMobileOpen(false)}
                    className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-navy-700 hover:bg-navy-50"
                  >
                    <User className="w-4 h-4" />
                    {user.role === "candidat" ? "Mon profil" : "Espace visiteur"}
                  </Link>
                  <button
                    onClick={() => { setMobileOpen(false); logout(); }}
                    className="flex min-h-11 items-center gap-2 rounded-lg px-3 text-left text-sm font-medium text-red-600 hover:bg-red-50"
                  >
                    <LogOut className="h-4 w-4" />
                    Se déconnecter
                  </button>
                </>
              ) : !ready ? (
                <span
                  aria-hidden="true"
                  className="h-11 animate-pulse rounded-lg bg-navy-50"
                />
              ) : (
                <>
                  <Link
                    href={loginHref}
                    onClick={() => setMobileOpen(false)}
                    className="flex min-h-11 items-center justify-center rounded-lg border border-navy-800 text-sm font-semibold text-navy-800 hover:bg-navy-50"
                  >
                    Connexion
                  </Link>
                  <Link
                    href={registerHref}
                    onClick={() => setMobileOpen(false)}
                    className="flex min-h-11 items-center justify-center rounded-xl bg-turquoise-500 text-sm font-semibold text-white transition-colors hover:bg-turquoise-600"
                  >
                    Créer un compte
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
