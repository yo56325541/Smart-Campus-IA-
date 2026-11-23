import * as React from "react";
import { cn } from "@/lib/utils/cn";

// ─── Card Container ───────────────────────────────────────────────────────────

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Ajoute un effet de survol (élévation + translate) */
  hoverable?: boolean;
  /** Supprime le padding interne */
  noPadding?: boolean;
  /** Ajoute une bordure de couleur en haut */
  accentTop?: boolean;
}

export function Card({
  hoverable = false,
  noPadding = false,
  accentTop = false,
  className,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "bg-white rounded-xl border border-border shadow-card",
        "transition-all duration-200",
        !noPadding && "p-6",
        accentTop && "border-t-2 border-t-turquoise-500",
        hoverable &&
          "cursor-pointer hover:shadow-lg hover:-translate-y-0.5 hover:border-turquoise-200",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

// ─── Card Header ─────────────────────────────────────────────────────────────

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Affiche une bordure en bas */
  withBorder?: boolean;
}

export function CardHeader({
  withBorder = false,
  className,
  children,
  ...props
}: CardHeaderProps) {
  return (
    <div
      className={cn(
        "px-6 pt-6 pb-4",
        withBorder && "border-b border-border pb-4",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

// ─── Card Body ────────────────────────────────────────────────────────────────

export function CardBody({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("px-6 py-4", className)} {...props}>
      {children}
    </div>
  );
}

// ─── Card Footer ─────────────────────────────────────────────────────────────

export function CardFooter({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "px-6 pb-6 pt-4 border-t border-border flex items-center gap-3",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

// ─── Card Title ───────────────────────────────────────────────────────────────

export function CardTitle({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn(
        "text-lg font-bold text-navy-800 leading-tight",
        className
      )}
      {...props}
    >
      {children}
    </h3>
  );
}

// ─── Card Description ─────────────────────────────────────────────────────────

export function CardDescription({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn("text-sm text-text-muted leading-relaxed mt-1", className)}
      {...props}
    >
      {children}
    </p>
  );
}
