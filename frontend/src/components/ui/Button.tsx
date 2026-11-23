import * as React from "react";
import { cn } from "@/lib/utils/cn";

// ─── Variants & Sizes ─────────────────────────────────────────────────────────

type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "danger";
type ButtonSize    = "sm" | "md" | "lg" | "icon";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-navy-800 text-white shadow-sm hover:bg-navy-700 active:bg-navy-900 " +
    "focus-visible:ring-2 focus-visible:ring-turquoise-500 focus-visible:ring-offset-2",

  secondary:
    "bg-turquoise-500 text-white shadow-sm hover:bg-turquoise-600 active:bg-turquoise-700 " +
    "focus-visible:ring-2 focus-visible:ring-turquoise-500 focus-visible:ring-offset-2",

  outline:
    "border border-navy-800 text-navy-800 bg-transparent hover:bg-navy-50 active:bg-navy-100 " +
    "focus-visible:ring-2 focus-visible:ring-navy-800 focus-visible:ring-offset-2",

  ghost:
    "text-navy-800 bg-transparent hover:bg-navy-50 active:bg-navy-100 " +
    "focus-visible:ring-2 focus-visible:ring-navy-800 focus-visible:ring-offset-2",

  danger:
    "bg-red-600 text-white shadow-sm hover:bg-red-700 active:bg-red-800 " +
    "focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm:   "h-8 px-3 text-sm gap-1.5 rounded-md",
  md:   "h-10 px-4 text-sm gap-2 rounded-lg",
  lg:   "h-12 px-6 text-base gap-2.5 rounded-xl",
  icon: "h-10 w-10 rounded-lg",
};

// ─── Spinner interne ──────────────────────────────────────────────────────────

function ButtonSpinner() {
  return (
    <svg
      className="animate-spin h-4 w-4 shrink-0"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12" cy="12" r="10"
        stroke="currentColor" strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
  as?: "button" | "a";
  href?: string;
}

// ─── Composant ────────────────────────────────────────────────────────────────

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      children,
      className,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          // Base
          "inline-flex items-center justify-center font-semibold",
          "outline-none transition-all duration-150",
          "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
          "select-none",
          // Variant + Size
          variantClasses[variant],
          sizeClasses[size],
          // Full width
          fullWidth && "w-full",
          className
        )}
        {...props}
      >
        {loading ? (
          <ButtonSpinner />
        ) : (
          leftIcon && <span className="shrink-0">{leftIcon}</span>
        )}
        {children && <span>{children}</span>}
        {!loading && rightIcon && (
          <span className="shrink-0">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
