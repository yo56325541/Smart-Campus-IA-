"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, LockKeyhole, Mail, UserRound } from "lucide-react";
import { useCampus } from "@/components/providers/CampusProvider";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

function getReturnTo(value: string | null) {
  return value === "/chat" || value?.startsWith("/chat?")
    ? value
    : "/chat";
}

function AuthShell({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div className="w-full max-w-md">
      <div className="mb-8 text-center">
        <h1 className="mb-2 text-2xl font-bold text-navy-800">{title}</h1>
        <p className="text-sm text-text-muted">{description}</p>
      </div>
      <div className="rounded-2xl border border-border bg-white p-6 shadow-card sm:p-8">
        {children}
        <div className="mt-6 border-t border-border pt-5 text-center">
          {footer}
        </div>
      </div>
      <div className="mt-6 text-center">
        <Link
          href="/"
          className="inline-flex min-h-11 items-center gap-1.5 text-sm text-text-muted transition-colors hover:text-navy-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500"
        >
          <ArrowLeft className="h-4 w-4" />
          Retour à l’accueil
        </Link>
      </div>
    </div>
  );
}

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, ready, startupError } = useCampus();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const returnTo = getReturnTo(searchParams.get("returnTo"));
  const registerHref = `/register?returnTo=${encodeURIComponent(returnTo)}`;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await login({ email, password });
      router.replace(
        result.user.role === "admin" ? "/admin/dashboard" : returnTo,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "La connexion a échoué. Réessayez.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell
      title="Connexion"
      description="Retrouvez votre espace d’orientation et vos conversations."
      footer={
        <p className="text-sm text-text-muted">
          Pas encore de compte ?{" "}
          <Link
            href={registerHref}
            className="font-semibold text-turquoise-700 hover:text-turquoise-800"
          >
            Créer un compte candidat
          </Link>
        </p>
      }
    >
      {startupError && (
        <Alert variant="error" title="Service indisponible" className="mb-5">
          {startupError}
        </Alert>
      )}
      {error && (
        <Alert variant="error" title="Connexion impossible" className="mb-5">
          {error}
        </Alert>
      )}
      <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
        <Input
          label="Adresse e-mail"
          type="email"
          name="email"
          autoComplete="email"
          required
          maxLength={255}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          leftIcon={<Mail className="h-4 w-4" />}
        />
        <Input
          label="Mot de passe"
          type="password"
          name="password"
          autoComplete="current-password"
          required
          minLength={1}
          maxLength={128}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          leftIcon={<LockKeyhole className="h-4 w-4" />}
        />
        <Button type="submit" fullWidth loading={submitting || !ready}>
          Se connecter
        </Button>
      </form>
    </AuthShell>
  );
}

export function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { register, ready, startupError } = useCampus();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const returnTo = getReturnTo(searchParams.get("returnTo"));
  const loginHref = `/login?returnTo=${encodeURIComponent(returnTo)}`;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register({
        full_name: fullName.trim(),
        email,
        password,
      });
      router.replace(returnTo);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "La création du compte a échoué. Réessayez.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell
      title="Créer un compte candidat"
      description="Votre conversation visiteur est conservée pendant le rattachement."
      footer={
        <p className="text-sm text-text-muted">
          Déjà un compte ?{" "}
          <Link
            href={loginHref}
            className="font-semibold text-turquoise-700 hover:text-turquoise-800"
          >
            Se connecter
          </Link>
        </p>
      }
    >
      {startupError && (
        <Alert variant="error" title="Service indisponible" className="mb-5">
          {startupError}
        </Alert>
      )}
      {error && (
        <Alert variant="error" title="Inscription impossible" className="mb-5">
          {error}
        </Alert>
      )}
      <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
        <Input
          label="Nom complet (facultatif)"
          type="text"
          name="full_name"
          autoComplete="name"
          maxLength={120}
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          leftIcon={<UserRound className="h-4 w-4" />}
        />
        <Input
          label="Adresse e-mail"
          type="email"
          name="email"
          autoComplete="email"
          required
          maxLength={255}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          leftIcon={<Mail className="h-4 w-4" />}
        />
        <Input
          label="Mot de passe"
          type="password"
          name="password"
          autoComplete="new-password"
          required
          minLength={8}
          maxLength={128}
          hint="8 à 128 caractères."
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          leftIcon={<LockKeyhole className="h-4 w-4" />}
        />
        <Button type="submit" variant="secondary" fullWidth loading={submitting || !ready}>
          Créer mon compte
        </Button>
        <p className="text-center text-xs leading-relaxed text-text-muted">
          Votre session visiteur et ses conversations seront transmises au
          compte si le Backend confirme le rattachement.
        </p>
      </form>
    </AuthShell>
  );
}
