"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowRight, BookOpen, Plus } from "lucide-react";
import { AdminPageHeader } from "@/components/admin/AdminPageHeader";
import { useCampus } from "@/components/providers/CampusProvider";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Select, Textarea } from "@/components/ui/Input";
import { CampusApiError } from "@/lib/api/campus";
import {
  createProgram,
  getPrograms,
  ProgramApiError,
} from "@/lib/api/programs";
import type { Institution, ProgramIn, ProgramOut } from "@/lib/types";

export default function AdminProgramsPage() {
  const { accessToken } = useCampus();
  const [programs, setPrograms] = useState<ProgramOut[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchPrograms = useCallback(async () => {
    if (!accessToken) {
      throw new Error("La session administrateur est absente. Reconnectez-vous.");
    }
    return getPrograms(
      { include_inactive: true, limit: 200 },
      accessToken,
    );
  }, [accessToken]);

  const loadPrograms = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPrograms(await fetchPrograms());
    } catch (requestError) {
      setError(
        requestError instanceof ProgramApiError ||
        requestError instanceof CampusApiError ||
        requestError instanceof Error
          ? requestError.message
          : "Impossible de charger le catalogue administrateur.",
      );
      setPrograms(null);
    } finally {
      setLoading(false);
    }
  }, [fetchPrograms]);

  useEffect(() => {
    let active = true;
    void Promise.resolve()
      .then(fetchPrograms)
      .then((result) => {
        if (active) setPrograms(result);
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        setError(
          requestError instanceof ProgramApiError ||
          requestError instanceof CampusApiError ||
          requestError instanceof Error
            ? requestError.message
            : "Impossible de charger le catalogue administrateur.",
        );
        setPrograms(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fetchPrograms]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) {
      setError("La session administrateur est absente. Reconnectez-vous.");
      return;
    }
    const form = event.currentTarget;
    const values = new FormData(form);
    const duration = String(values.get("duration_years") ?? "");
    const body: ProgramIn = {
      slug: String(values.get("slug") ?? "").trim(),
      institution: String(values.get("institution") ?? "IIT") as Institution,
      level: String(values.get("level") ?? "").trim(),
      name: String(values.get("name") ?? "").trim(),
      description: String(values.get("description") ?? "").trim(),
      duration_years: duration === "" ? null : Number(duration),
      language: String(values.get("language") ?? "fr").trim(),
      careers: String(values.get("careers") ?? "").trim(),
      is_active: true,
    };

    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      const created = await createProgram(body, accessToken);
      setPrograms((current) => [created, ...(current ?? [])].slice(0, 200));
      setSuccess(`La formation « ${created.name} » a été créée.`);
      form.reset();
    } catch (requestError) {
      setError(
        requestError instanceof ProgramApiError
          ? requestError.message
          : "La création de la formation a échoué.",
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <AdminPageHeader
        title="Gestion des formations"
        description="Le Backend réserve la création, la modification et la désactivation des formations aux administrateurs."
        icon={BookOpen}
      />

      {error && (
        <Alert variant="error" title="Action impossible" className="mb-5">
          <p>{error}</p>
          {programs === null && (
            <Button className="mt-3" size="sm" onClick={() => void loadPrograms()}>
              Réessayer
            </Button>
          )}
        </Alert>
      )}
      {success && (
        <Alert variant="success" title="Modification enregistrée" className="mb-5">
          {success}
        </Alert>
      )}

      <Card className="mb-8">
        <h2 className="mb-5 flex items-center gap-2 text-lg font-bold text-navy-800">
          <Plus className="h-5 w-5 text-turquoise-700" aria-hidden="true" />
          Ajouter une formation
        </h2>
        <form onSubmit={handleCreate} className="grid gap-4 md:grid-cols-2">
          <Input
            label="Nom de la formation"
            name="name"
            maxLength={200}
            required
          />
          <Input
            label="Slug"
            name="slug"
            maxLength={120}
            pattern="[a-z0-9]+(-[a-z0-9]+)*"
            hint="Minuscules, chiffres et tirets."
            required
          />
          <Select label="Établissement" name="institution" defaultValue="IIT">
            <option value="IIT">IIT</option>
            <option value="ISB">ISB</option>
          </Select>
          <Input label="Niveau" name="level" maxLength={50} required />
          <Input
            label="Durée (années)"
            name="duration_years"
            type="number"
            min={1}
            max={10}
          />
          <Input label="Langue" name="language" defaultValue="fr" maxLength={50} required />
          <Textarea
            label="Description"
            name="description"
            className="md:col-span-2"
          />
          <Textarea
            label="Débouchés"
            name="careers"
            className="md:col-span-2"
          />
          <div className="md:col-span-2">
            <Button type="submit" loading={creating} leftIcon={<Plus className="h-4 w-4" />}>
              Créer la formation
            </Button>
          </div>
        </form>
      </Card>

      <Card noPadding>
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-border p-5">
          <div>
            <h2 className="text-lg font-bold text-navy-800">Catalogue géré</h2>
            <p className="mt-1 text-sm text-text-muted">
              {programs?.length === 200
                ? "Les 200 formations les plus récentes du catalogue sont chargées."
                : programs
                  ? `${programs.length} formation${programs.length === 1 ? "" : "s"} chargée${programs.length === 1 ? "" : "s"}.`
                  : "Chargement…"}
            </p>
          </div>
          <Badge variant="info">Actives et désactivées</Badge>
        </div>

        {loading && (
          <div className="space-y-3 p-5" aria-live="polite">
            <div className="h-12 animate-pulse rounded-lg bg-navy-50" />
            <div className="h-12 animate-pulse rounded-lg bg-navy-50" />
          </div>
        )}

        {!loading && programs?.length === 0 && (
          <p className="p-8 text-center text-sm text-text-muted">
            Aucune formation n’est enregistrée. Vous pouvez en ajouter une avec le formulaire ci-dessus.
          </p>
        )}

        {!loading && programs && programs.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-navy-50 text-xs uppercase tracking-wide text-navy-700">
                <tr>
                  <th scope="col" className="px-5 py-3">Formation</th>
                  <th scope="col" className="px-5 py-3">Établissement</th>
                  <th scope="col" className="px-5 py-3">Niveau</th>
                  <th scope="col" className="px-5 py-3">État</th>
                  <th scope="col" className="px-5 py-3"><span className="sr-only">Gérer</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {programs.map((program) => (
                  <tr key={program.id}>
                    <td className="px-5 py-4">
                      <p className="font-semibold text-navy-800">{program.name}</p>
                      <p className="mt-1 text-xs text-text-muted">{program.slug}</p>
                    </td>
                    <td className="px-5 py-4">
                      <Badge variant={program.institution === "IIT" ? "primary" : "secondary"}>
                        {program.institution}
                      </Badge>
                    </td>
                    <td className="px-5 py-4 text-text-muted">{program.level}</td>
                    <td className="px-5 py-4">
                      <Badge variant={program.is_active ? "success" : "default"} dot>
                        {program.is_active ? "Active" : "Désactivée"}
                      </Badge>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        href={`/admin/programmes/${encodeURIComponent(program.slug)}`}
                        className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold text-turquoise-700 hover:bg-turquoise-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-turquoise-500"
                      >
                        Gérer
                        <ArrowRight className="h-4 w-4" aria-hidden="true" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
