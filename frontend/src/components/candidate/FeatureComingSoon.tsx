import { Clock3 } from "lucide-react";
import { Card } from "@/components/ui/Card";

export function FeatureComingSoon({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card className="border-navy-100">
      <div className="flex items-start gap-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-turquoise-50 text-turquoise-700">
          <Clock3 className="h-5 w-5" />
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-turquoise-700">
            Fonctionnalité à venir
          </p>
          <h2 className="mt-1 text-lg font-bold text-navy-800">{title}</h2>
          <p className="mt-2 text-sm leading-relaxed text-text-muted">
            {description}
          </p>
        </div>
      </div>
    </Card>
  );
}
