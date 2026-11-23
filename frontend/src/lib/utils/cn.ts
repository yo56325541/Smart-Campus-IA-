import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Fusionne des classes Tailwind intelligemment.
 * Utilise clsx pour les conditions et twMerge pour résoudre les conflits.
 *
 * @example
 * cn("px-4 py-2", isActive && "bg-navy-800", "hover:bg-navy-700")
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
