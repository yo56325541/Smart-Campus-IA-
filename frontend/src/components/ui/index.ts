/**
 * Barrel export — Composants UI SmartCampus AI
 *
 * Usage: import { Button, Card, Badge, ... } from "@/components/ui"
 */

export { Button }              from "./Button";
export type { ButtonProps }    from "./Button";

export {
  Card, CardHeader, CardBody, CardFooter, CardTitle, CardDescription,
}                              from "./Card";
export type { CardProps }      from "./Card";

export { Badge, StatusBadge, statusLabels } from "./Badge";
export type { BadgeProps }     from "./Badge";

export { Input, Textarea, Select } from "./Input";
export type { InputProps, TextareaProps, SelectProps } from "./Input";

export { Spinner, FullPageSpinner, CenteredSpinner } from "./Spinner";
export type { SpinnerProps }   from "./Spinner";

export { Alert, ApiErrorAlert } from "./Alert";
export type { AlertProps }     from "./Alert";
