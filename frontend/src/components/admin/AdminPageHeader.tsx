import type { LucideIcon } from "lucide-react";

export function AdminPageHeader({
  title,
  description,
  icon: Icon,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
}) {
  return (
    <header className="mb-8">
      <div className="mb-2 flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-turquoise-50 text-turquoise-700">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <h1 className="text-2xl font-bold text-navy-800">{title}</h1>
      </div>
      <p className="text-sm leading-6 text-text-muted">{description}</p>
    </header>
  );
}
