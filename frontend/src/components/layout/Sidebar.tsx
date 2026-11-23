"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  BookOpen,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Compass,
  FileText,
  GraduationCap,
  LayoutDashboard,
  MessageSquare,
  Settings,
  UserRound,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { UserOut } from "@/lib/types";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SidebarItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string | number;
  exact?: boolean;
}

export interface SidebarSection {
  title?: string;
  items: SidebarItem[];
}

// ─── Navigation Admin ─────────────────────────────────────────────────────────

export const adminSections: SidebarSection[] = [
  {
    items: [
      {
        label: "Tableau de bord",
        href: "/admin/dashboard",
        icon: <LayoutDashboard className="w-4.5 h-4.5" />,
        exact: false,
      },
    ],
  },
  {
    title: "Catalogue",
    items: [
      {
        label: "Formations",
        href: "/admin/programmes",
        icon: <BookOpen className="w-4.5 h-4.5" />,
      },
    ],
  },
  {
    title: "Candidatures",
    items: [
      {
        label: "Toutes les candidatures",
        href: "/admin/candidatures",
        icon: <FileText className="w-4.5 h-4.5" />,
      },
    ],
  },
  {
    title: "Utilisateurs",
    items: [
      {
        label: "Gestion des comptes",
        href: "/admin/utilisateurs",
        icon: <Users className="w-4.5 h-4.5" />,
      },
    ],
  },
  {
    title: "Espaces à venir",
    items: [
      {
        label: "Académique IIT",
        href: "/admin/espaces/academique-iit",
        icon: <GraduationCap className="w-4.5 h-4.5" />,
      },
      {
        label: "Académique ISB",
        href: "/admin/espaces/academique-isb",
        icon: <BookOpen className="w-4.5 h-4.5" />,
      },
      {
        label: "Entretien",
        href: "/admin/espaces/entretien",
        icon: <MessageSquare className="w-4.5 h-4.5" />,
      },
      {
        label: "Direction",
        href: "/admin/espaces/direction",
        icon: <LayoutDashboard className="w-4.5 h-4.5" />,
      },
    ],
  },
];

// ─── Navigation Candidat ──────────────────────────────────────────────────────

export const candidatSections: SidebarSection[] = [
  {
    items: [
      {
        label: "Tableau de bord",
        href: "/dashboard",
        icon: <LayoutDashboard className="w-4.5 h-4.5" />,
        exact: true,
      },
    ],
  },
  {
    title: "Mon espace",
    items: [
      {
        label: "Mon profil",
        href: "/profil",
        icon: <UserRound className="w-4.5 h-4.5" />,
      },
      {
        label: "Mes conversations",
        href: "/conversations",
        icon: <MessageSquare className="w-4.5 h-4.5" />,
      },
    ],
  },
  {
    title: "Mes démarches",
    items: [
      {
        label: "Mes candidatures",
        href: "/candidatures",
        icon: <FileText className="w-4.5 h-4.5" />,
      },
      {
        label: "Catalogue des formations",
        href: "/programmes",
        icon: <BookOpen className="w-4.5 h-4.5" />,
      },
    ],
  },
  {
    title: "À venir",
    items: [
      {
        label: "Orientation personnalisée",
        href: "/fonctionnalites/orientation",
        icon: <Compass className="w-4.5 h-4.5" />,
      },
      {
        label: "QCM d’orientation",
        href: "/fonctionnalites/qcm",
        icon: <ClipboardList className="w-4.5 h-4.5" />,
      },
      {
        label: "Rendez-vous",
        href: "/fonctionnalites/rendez-vous",
        icon: <CalendarDays className="w-4.5 h-4.5" />,
      },
      {
        label: "Notifications",
        href: "/fonctionnalites/notifications",
        icon: <Bell className="w-4.5 h-4.5" />,
      },
    ],
  },
];

// ─── SidebarLink ──────────────────────────────────────────────────────────────

function SidebarLink({
  item,
  collapsed,
  onNavigate,
}: {
  item: SidebarItem;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const isActive = item.exact
    ? pathname === item.href
    : pathname.startsWith(item.href);

  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      title={collapsed ? item.label : undefined}
      className={cn(
        "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium",
        "transition-all duration-150 group relative",
        isActive
          ? "bg-turquoise-500 text-white shadow-sm"
          : "text-navy-200 hover:bg-navy-700 hover:text-white"
      )}
    >
      <span className={cn("shrink-0", isActive ? "text-white" : "text-navy-400 group-hover:text-white")}>
        {item.icon}
      </span>

      {!collapsed && (
        <span className="flex-1 truncate">{item.label}</span>
      )}

      {!collapsed && item.badge !== undefined && (
        <span className={cn(
          "text-xs font-bold px-1.5 py-0.5 rounded-full min-w-5 text-center",
          isActive ? "bg-white/20 text-white" : "bg-navy-600 text-navy-200"
        )}>
          {item.badge}
        </span>
      )}

      {/* Tooltip en mode collapsed */}
      {collapsed && (
        <span className="absolute left-full ml-3 px-2.5 py-1.5 bg-navy-900 text-white text-xs font-medium rounded-lg whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-150 z-50 shadow-lg">
          {item.label}
        </span>
      )}
    </Link>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

export interface SidebarProps {
  sections?: SidebarSection[];
  user?: UserOut | null;
  defaultCollapsed?: boolean;
  onNavigate?: () => void;
}

// ─── Composant ────────────────────────────────────────────────────────────────

export function Sidebar({
  sections = adminSections,
  user = null,
  defaultCollapsed = false,
  onNavigate,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  const initials = user?.full_name
    ? user.full_name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase()
    : user?.email?.[0].toUpperCase() ?? "?";

  return (
    <aside
      className={cn(
        "flex flex-col h-full bg-navy-800 text-white",
        "transition-all duration-300 ease-out",
        "border-r border-navy-700",
        collapsed ? "w-16" : "w-64"
      )}
      aria-label="Navigation latérale"
    >

      {/* En-tête Sidebar */}
      <div className={cn(
        "flex items-center gap-3 px-4 py-5 border-b border-navy-700",
        collapsed && "justify-center px-2"
      )}>
        <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-turquoise-500 text-white shrink-0">
          <GraduationCap className="w-4.5 h-4.5" />
        </span>
        {!collapsed && (
          <div className="flex flex-col leading-tight min-w-0">
            <span className="text-sm font-bold tracking-tight truncate">SmartCampus</span>
            <span className="text-[9px] font-semibold text-turquoise-400 tracking-widest uppercase">AI</span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto scrollbar-thin py-4 px-2 flex flex-col gap-6">
        {sections.map((section, i) => (
          <div key={i} className="flex flex-col gap-1">
            {!collapsed && section.title && (
              <p className="text-[10px] font-bold text-navy-500 uppercase tracking-widest px-3 mb-1">
                {section.title}
              </p>
            )}
            {section.items.map(item => (
              <SidebarLink
                key={item.href}
                item={item}
                collapsed={collapsed}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        ))}
      </nav>

      {/* Profil utilisateur */}
      {user && (
        <div className={cn(
          "border-t border-navy-700 p-3",
          collapsed && "flex justify-center"
        )}>
          {!collapsed ? (
            <div className="flex items-center gap-3 p-2 rounded-xl transition-colors group">
              <span className="flex items-center justify-center w-8 h-8 rounded-full bg-turquoise-500 text-white text-xs font-bold shrink-0">
                {initials}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">
                  {user.full_name || user.email}
                </p>
                <p className="text-xs text-navy-400 capitalize">{user.role}</p>
              </div>
              {user.role === "candidat" && (
                <Link
                  href="/profil"
                  aria-label="Mon profil"
                  className="text-navy-400 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-400"
                >
                  <Settings className="w-4 h-4" />
                </Link>
              )}
            </div>
          ) : (
            <span
              title={user.full_name || user.email}
              className="flex items-center justify-center w-9 h-9 rounded-full bg-turquoise-500 text-white text-xs font-bold cursor-pointer hover:bg-turquoise-600 transition-colors"
            >
              {initials}
            </span>
          )}
        </div>
      )}

      {/* Bouton collapse */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className={cn(
          "flex items-center justify-center h-10 border-t border-navy-700",
          "text-navy-400 hover:text-white hover:bg-navy-700 transition-colors",
          "text-xs gap-1.5 font-medium"
        )}
        aria-label={collapsed ? "Développer la sidebar" : "Réduire la sidebar"}
      >
        {collapsed ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <>
            <ChevronLeft className="w-4 h-4" />
            <span>Réduire</span>
          </>
        )}
      </button>
    </aside>
  );
}

// ─── Overlay mobile ───────────────────────────────────────────────────────────

export function SidebarOverlay({
  open,
  onClose,
  sections,
  user,
}: {
  open: boolean;
  onClose: () => void;
  sections?: SidebarSection[];
  user?: UserOut | null;
}) {
  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-navy-950/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Drawer */}
      <div className="fixed inset-y-0 left-0 z-50 flex animate-slide-left">
        <Sidebar sections={sections} user={user} onNavigate={onClose} />
        <button
          onClick={onClose}
          className="ml-2 mt-4 flex items-center justify-center w-8 h-8 rounded-lg bg-white/10 text-white hover:bg-white/20 transition-colors"
          aria-label="Fermer le menu"
        >
          ✕
        </button>
      </div>
    </>
  );
}
