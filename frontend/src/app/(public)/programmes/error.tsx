"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";

export default function ProgramsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Erreur de chargement des formations :", error);
  }, [error]);

  return (
    <div className="container-page flex min-h-96 flex-col items-center justify-center py-12">
      <div className="w-full max-w-xl">
        <Alert variant="error" title="Le catalogue est momentanément indisponible">
          Impossible de charger les informations des formations. Réessayez dans
          quelques instants.
        </Alert>
        <div className="mt-5 flex flex-wrap gap-3">
          <Button onClick={reset}>Réessayer</Button>
          <Link href="/programmes">
            <Button variant="outline">Retour au catalogue</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
