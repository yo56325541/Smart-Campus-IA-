import * as React from "react";
import { cn } from "@/lib/utils/cn";

// ─── Variants ─────────────────────────────────────────────────────────────────

type SpinnerSize = "xs" | "sm" | "md" | "lg" | "xl";
type SpinnerVariant = "navy" | "turquoise" | "white" | "muted";

const sizeClasses: Record<SpinnerSize, string> = {
  xs: "w-3 h-3 border-[1.5px]",
  sm: "w-4 h-4 border-2",
  md: "w-6 h-6 border-2",
  lg: "w-8 h-8 border-[3px]",
  xl: "w-12 h-12 border-4",
};

const colorClasses: Record<SpinnerVariant, string> = {
  navy:      "border-navy-200 border-t-navy-800",
  turquoise: "border-turquoise-200 border-t-turquoise-500",
  white:     "border-white/30 border-t-white",
  muted:     "border-slate-200 border-t-slate-500",
};

// ─── Props ────────────────────────────────────────────────────────────────────

export interface SpinnerProps {
  size?: SpinnerSize;
  variant?: SpinnerVariant;
  label?: string;
  className?: string;
}

// ─── Composant ────────────────────────────────────────────────────────────────

export function Spinner({
  size = "md",
  variant = "turquoise",
  label = "Chargement...",
  className,
}: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label={label}
      className={cn("inline-flex items-center justify-center", className)}
    >
      <span
        className={cn(
          "rounded-full animate-spin",
          sizeClasses[size],
          colorClasses[variant]
        )}
        aria-hidden="true"
      />
      <span className="sr-only">{label}</span>
    </span>
  );
}

// ─── Overlay de chargement pleine page ────────────────────────────────────────

export function FullPageSpinner({ label = "Chargement..." }: { label?: string }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg/80 backdrop-blur-sm"
      role="status"
      aria-label={label}
    >
      <div className="flex flex-col items-center gap-4">
        <Spinner size="xl" variant="turquoise" />
        <p className="text-sm font-medium text-text-muted animate-pulse-soft">
          {label}
        </p>
      </div>
    </div>
  );
}

// ─── Spinner centré dans un conteneur ────────────────────────────────────────

export function CenteredSpinner({
  label,
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-3 py-16", className)}
      role="status"
    >
      <Spinner size="lg" variant="turquoise" />
      {label && (
        <p className="text-sm text-text-muted">{label}</p>
      )}
    </div>
  );
}
