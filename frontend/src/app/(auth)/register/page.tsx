import type { Metadata } from "next";
import { Suspense } from "react";
import { RegisterForm } from "@/components/auth/AuthForms";

export const metadata: Metadata = {
  title: "Créer un compte candidat",
  description: "Créez un compte candidat en conservant votre conversation visiteur.",
};

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="w-full max-w-md animate-pulse rounded-2xl bg-white p-8">
          <div className="mx-auto h-7 w-48 rounded bg-navy-50" />
          <div className="mt-8 h-11 rounded bg-navy-50" />
        </div>
      }
    >
      <RegisterForm />
    </Suspense>
  );
}
