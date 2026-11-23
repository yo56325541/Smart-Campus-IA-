import { Clock3 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

export function FeatureComingSoonCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card className="h-full">
      <div className="mb-3 flex items-start justify-between gap-3">
        <h2 className="font-semibold text-navy-800">{title}</h2>
        <Badge variant="warning" size="sm">
          <Clock3 className="h-3 w-3" aria-hidden="true" />
          Fonctionnalité à venir
        </Badge>
      </div>
      <p className="text-sm leading-6 text-text-muted">{description}</p>
    </Card>
  );
}
