import { Card } from "@/components/ui/Card";
import { CenteredSpinner } from "@/components/ui/Spinner";

export default function ProgramsLoading() {
  return (
    <div className="container-page py-10" aria-busy="true">
      <CenteredSpinner label="Chargement du catalogue des formations..." />
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {[1, 2, 3].map((item) => (
          <Card key={item} className="animate-pulse">
            <div className="mb-4 h-6 w-20 rounded bg-navy-50" />
            <div className="mb-3 h-6 w-3/4 rounded bg-navy-50" />
            <div className="h-4 w-full rounded bg-navy-50" />
            <div className="mt-2 h-4 w-2/3 rounded bg-navy-50" />
          </Card>
        ))}
      </div>
    </div>
  );
}
