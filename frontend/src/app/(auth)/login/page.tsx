import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/components/auth/AuthForms";

export const metadata: Metadata = {
  title: "Connexion",
  description: "Connectez-vous pour retrouver votre espace candidat.",
};

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="w-full max-w-md animate-pulse rounded-2xl bg-white p-8">
          <div className="mx-auto h-7 w-40 rounded bg-navy-50" />
          <div className="mt-8 h-11 rounded bg-navy-50" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
