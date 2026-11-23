import * as React from "react";
import { type ApplicationStatus } from "@/lib/types";
import { cn } from "@/lib/utils/cn";

// ─── Variants ─────────────────────────────────────────────────────────────────

type BadgeVariant =
  | "default"
  | "primary"
  | "secondary"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "outline"
  // Statuts candidature
  | "draft"
  | "submitted"
  | "under_review"
  | "accepted"
  | "rejected";

type BadgeSize = "sm" | "md";

const variantClasses: Record<BadgeVariant, string> = {
  default:      "bg-slate-100 text-slate-700 border-slate-200",
  primary:      "bg-navy-100 text-navy-800 border-navy-200",
  secondary:    "bg-turquoise-100 text-turquoise-700 border-turquoise-200",
  success:      "bg-emerald-100 text-emerald-700 border-emerald-200",
  warning:      "bg-amber-100 text-amber-700 border-amber-200",
  danger:       "bg-red-100 text-red-700 border-red-200",
  info:         "bg-blue-100 text-blue-700 border-blue-200",
  outline:      "bg-transparent text-navy-800 border-navy-300",
  // Statuts candidature
  draft:        "bg-slate-100 text-slate-600 border-slate-200",
  submitted:    "bg-blue-100 text-blue-700 border-blue-200",
  under_review: "bg-amber-100 text-amber-700 border-amber-200",
  accepted:     "bg-emerald-100 text-emerald-700 border-emerald-200",
  rejected:     "bg-red-100 text-red-700 border-red-200",
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "text-xs px-2 py-0.5 rounded-md",
  md: "text-xs px-2.5 py-1 rounded-lg",
};

// ─── Labels pour les statuts candidature ─────────────────────────────────────

export const statusLabels: Record<ApplicationStatus, string> = {
  draft:        "Brouillon",
  submitted:    "Soumise",
  under_review: "En cours",
  accepted:     "Acceptée",
  rejected:     "Refusée",
};

// ─── Props ────────────────────────────────────────────────────────────────────

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
}

// ─── Composant ────────────────────────────────────────────────────────────────

export function Badge({
  variant = "default",
  size = "md",
  dot = false,
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-semibold border",
        "whitespace-nowrap select-none",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {dot && (
        <span
          className="w-1.5 h-1.5 rounded-full bg-current opacity-80 shrink-0"
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}

// ─── Badge Statut Candidature (raccourci) ────────────────────────────────────

export function StatusBadge({
  status,
  size = "md",
  className,
}: {
  status: ApplicationStatus;
  size?: BadgeSize;
  className?: string;
}) {
  return (
    <Badge variant={status} size={size} dot className={className}>
      {statusLabels[status]}
    </Badge>
  );
}
