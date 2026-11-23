"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, BookOpen, Plus, Save, Trash2 } from "lucide-react";
import { AdminPageHeader } from "@/components/admin/AdminPageHeader";
import { useCampus } from "@/components/providers/CampusProvider";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Select, Textarea } from "@/components/ui/Input";
import {
  createAdmissionCondition,
  createTariff,
  deactivateProgram,
  deleteAdmissionCondition,
  deleteTariff,
  getAdmissionConditions,
  getProgram,
  getTariffs,
  ProgramApiError,
  updateAdmissionCondition,
  updateProgram,
  updateTariff,
} from "@/lib/api/programs";
import type {
  ConditionIn,
  ConditionOut,
  ConditionUpdate,
  Institution,
  ProgramDetail,
  ProgramUpdate,
  TariffIn,
  TariffOut,
  TariffUpdate,
} from "@/lib/types";

function apiError(error: unknown, fallback: string) {
  return error instanceof ProgramApiError ? error.message : fallback;
}

export default function AdminProgramDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { accessToken } = useCampus();
  const [program, setProgram] = useState<ProgramDetail | null>(null);
  const [conditions, setConditions] = useState<ConditionOut[] | null>(null);
  const [tariffs, setTariffs] = useState<TariffOut[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchProgram = useCallback(async () => {
    if (!accessToken) {
      throw new Error("La session administrateur est absente. Reconnectez-vous.");
    }
    const [programResult, conditionResult, tariffResult] = await Promise.all([
      getProgram(slug, accessToken),
      getAdmissionConditions(slug, accessToken),
      getTariffs(slug, accessToken),
    ]);
    return {
      program: programResult,
      conditions: conditionResult,
      tariffs: tariffResult,
    };
  }, [accessToken, slug]);

  const loadProgram = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchProgram();
      setProgram(result.program);
      setConditions(result.conditions);
      setTariffs(result.tariffs);
    } catch (requestError) {
      setError(apiError(requestError, "Impossible de charger cette formation."));
      setProgram(null);
      setConditions(null);
      setTariffs(null);
    } finally {
      setLoading(false);
    }
  }, [fetchProgram]);

  useEffect(() => {
    let active = true;
    void Promise.resolve()
      .then(fetchProgram)
      .then((result) => {
        if (!active) return;
        setProgram(result.program);
        setConditions(result.conditions);
        setTariffs(result.tariffs);
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        setError(apiError(requestError, "Impossible de charger cette formation."));
        setProgram(null);
        setConditions(null);
        setTariffs(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fetchProgram]);

  async function handleProgramUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !program) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    const duration = String(values.get("duration_years") ?? "");
    const body: ProgramUpdate = {
      name: String(values.get("name") ?? "").trim(),
      institution: String(values.get("institution") ?? "IIT") as Institution,
      level: String(values.get("level") ?? "").trim(),
      description: String(values.get("description") ?? "").trim(),
      duration_years: duration === "" ? null : Number(duration),
      language: String(values.get("language") ?? "").trim(),
      careers: String(values.get("careers") ?? "").trim(),
      is_active: values.get("is_active") === "on",
    };

    setBusyAction("program");
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateProgram(program.slug, body, accessToken);
      setProgram((current) => current ? { ...current, ...updated } : current);
      setSuccess("Les informations de la formation ont été mises à jour.");
    } catch (requestError) {
      setError(apiError(requestError, "La mise à jour de la formation a échoué."));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleProgramDeactivation() {
    if (!accessToken || !program || !program.is_active) return;
    if (!window.confirm("Désactiver cette formation ? Elle restera dans l’historique administratif.")) {
      return;
    }
    setBusyAction("program");
    setError(null);
    setSuccess(null);
    try {
      await deactivateProgram(program.slug, accessToken);
      setProgram((current) => current ? { ...current, is_active: false } : current);
      setSuccess("La formation a été désactivée sans suppression de son historique.");
    } catch (requestError) {
      setError(apiError(requestError, "La désactivation de la formation a échoué."));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCreateCondition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !program) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    const body: ConditionIn = {
      title: String(values.get("title") ?? "").trim(),
      description: String(values.get("description") ?? "").trim(),
      required_diploma: String(values.get("required_diploma") ?? "").trim() || null,
      min_average: String(values.get("min_average") ?? "").trim() || null,
      position: Number(values.get("position") ?? 0),
    };

    setBusyAction("condition-create");
    setError(null);
    setSuccess(null);
    try {
      const created = await createAdmissionCondition(program.slug, body, accessToken);
      setConditions((current) => [...(current ?? []), created]);
      setSuccess("La condition d’admission a été ajoutée.");
      form.reset();
    } catch (requestError) {
      setError(apiError(requestError, "L’ajout de la condition a échoué."));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleConditionUpdate(
    event: FormEvent<HTMLFormElement>,
    condition: ConditionOut,
  ) {
    event.preventDefault();
    if (!accessToken) return;
    const values = new FormData(event.currentTarget);
    const body: ConditionUpdate = {
      title: String(values.get("title") ?? "").trim(),
      description: String(values.get("description") ?? "").trim(),
      required_diploma: String(values.get("required_diploma") ?? "").trim() || null,
      min_average: String(values.get("min_average") ?? "").trim() || null,
      position: Number(values.get("position") ?? 0),
    };

    setBusyAction(`condition-${condition.id}`);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateAdmissionCondition(condition.id, body, accessToken);
      setConditions((current) =>
        current?.map((item) => item.id === updated.id ? updated : item) ?? [],
      );
      setSuccess("La condition d’admission a été modifiée.");
    } catch (requestError) {
      setError(apiError(requestError, "La modification de la condition a échoué."));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleConditionDelete(condition: ConditionOut) {
    if (!accessToken) return;
    if (!window.confirm(`Supprimer la condition « ${condition.title} » ?`)) return;
    setBusyAction(`condition-${condition.id}`);
    setError(null);
    setSuccess(null);
    try {
      await deleteAdmissionCondition(condition.id, accessToken);
      setConditions((current) => current?.filter((item) => item.id !== condition.id) ?? []);
      setSuccess("La condition d’admission a été supprimée.");
    } catch (requestError) {
      setError(apiError(requestError, "La suppression de la condition a échoué."));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCreateTariff(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !program) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    const body: TariffIn = {
      academic_year: String(values.get("academic_year") ?? "").trim(),
      amount: String(values.get("amount") ?? "").trim(),
      registration_fee: String(values.get("registration_fee") ?? "").trim() || null,
      currency: String(values.get("currency") ?? "TND").trim().toUpperCase(),
      payment_terms: String(values.get("payment_terms") ?? "").trim() || null,
    };

    setBusyAction("tariff-create");
    setError(null);
    setSuccess(null);
    try {
      const created = await createTariff(program.slug, body, accessToken);
      setTariffs((current) => [created, ...(current ?? [])]);
      setSuccess("Le tarif a été ajouté.");
      form.reset();
    } catch (requestError) {
      setError(apiError(requestError, "L’ajout du tarif a échoué."));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleTariffUpdate(
    event: FormEvent<HTMLFormElement>,
    tariff: TariffOut,
  ) {
    event.preventDefault();
    if (!accessToken) return;
    const values = new FormData(event.currentTarget);
    const body: TariffUpdate = {
      amount: String(values.get("amount") ?? "").trim(),
      registration_fee: String(values.get("registration_fee") ?? "").trim() || null,
      currency: String(values.get("currency") ?? "").trim().toUpperCase(),
      payment_terms: String(values.get("payment_terms") ?? "").trim() || null,
    };

    setBusyAction(`tariff-${tariff.id}`);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateTariff(tariff.id, body, accessToken);
      setTariffs((current) =>
        current?.map((item) => item.id === updated.id ? updated : item) ?? [],
      );
      setSuccess("Le tarif a été modifié.");
    } catch (requestError) {
      setError(apiError(requestError, "La modification du tarif a échoué."));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleTariffDelete(tariff: TariffOut) {
    if (!accessToken) return;
    if (!window.confirm(`Supprimer le tarif de l’année ${tariff.academic_year} ?`)) return;
    setBusyAction(`tariff-${tariff.id}`);
    setError(null);
    setSuccess(null);
    try {
      await deleteTariff(tariff.id, accessToken);
      setTariffs((current) => current?.filter((item) => item.id !== tariff.id) ?? []);
      setSuccess("Le tarif a été supprimé.");
    } catch (requestError) {
      setError(apiError(requestError, "La suppression du tarif a échoué."));
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="animate-fade-in">
      <Link
        href="/admin/programmes"
        className="mb-5 inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold text-navy-700 hover:bg-navy-50"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Retour au catalogue
      </Link>

      {error && (
        <Alert variant="error" title="Action impossible" className="mb-5">
          <p>{error}</p>
          {!program && (
            <Button className="mt-3" size="sm" onClick={() => void loadProgram()}>
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

      {loading && (
        <div className="space-y-5" aria-live="polite">
          <Card className="h-56 animate-pulse bg-navy-50" />
          <Card className="h-56 animate-pulse bg-navy-50" />
        </div>
      )}

      {!loading && !program && !error && (
        <Card>
          <p className="text-center text-sm text-text-muted">
            Cette formation n’est pas disponible.
          </p>
        </Card>
      )}

      {!loading && program && (
        <>
          <AdminPageHeader
            title={program.name}
            description={`Gestion de ${program.institution} · ${program.slug}`}
            icon={BookOpen}
          />

          <Card className="mb-6">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-bold text-navy-800">Informations générales</h2>
              <Badge variant={program.is_active ? "success" : "default"} dot>
                {program.is_active ? "Active" : "Désactivée"}
              </Badge>
            </div>
            <form
              key={`${program.id}-${program.is_active}`}
              onSubmit={handleProgramUpdate}
              className="grid gap-4 md:grid-cols-2"
            >
              <Input label="Nom" name="name" defaultValue={program.name} maxLength={200} required />
              <Input label="Slug (non modifiable)" value={program.slug} disabled readOnly />
              <Select label="Établissement" name="institution" defaultValue={program.institution}>
                <option value="IIT">IIT</option>
                <option value="ISB">ISB</option>
              </Select>
              <Input label="Niveau" name="level" defaultValue={program.level} maxLength={50} required />
              <Input
                label="Durée (années)"
                name="duration_years"
                type="number"
                min={1}
                max={10}
                defaultValue={program.duration_years ?? ""}
              />
              <Input label="Langue" name="language" defaultValue={program.language} maxLength={50} required />
              <Textarea
                label="Description"
                name="description"
                defaultValue={program.description}
                className="md:col-span-2"
              />
              <Textarea
                label="Débouchés"
                name="careers"
                defaultValue={program.careers}
                className="md:col-span-2"
              />
              <label className="flex min-h-10 items-center gap-3 text-sm font-semibold text-navy-800 md:col-span-2">
                <input
                  type="checkbox"
                  name="is_active"
                  defaultChecked={program.is_active}
                  className="h-4 w-4 accent-turquoise-600"
                />
                Formation active dans le catalogue public
              </label>
              <div className="flex flex-wrap gap-3 md:col-span-2">
                <Button
                  type="submit"
                  loading={busyAction === "program"}
                  disabled={busyAction !== null && busyAction !== "program"}
                  leftIcon={<Save className="h-4 w-4" />}
                >
                  Enregistrer les modifications
                </Button>
                {program.is_active && (
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busyAction !== null}
                    onClick={() => void handleProgramDeactivation()}
                  >
                    Désactiver
                  </Button>
                )}
              </div>
            </form>
          </Card>

          <div className="mb-6 grid gap-6 xl:grid-cols-2">
            <Card>
              <h2 className="mb-4 text-lg font-bold text-navy-800">Conditions d’admission</h2>
              <form onSubmit={handleCreateCondition} className="mb-6 grid gap-3 border-b border-border pb-6">
                <Input label="Titre" name="title" maxLength={200} required />
                <Textarea label="Description" name="description" />
                <Input label="Diplôme requis" name="required_diploma" maxLength={120} />
                <Input
                  label="Moyenne minimale"
                  name="min_average"
                  type="number"
                  min={0}
                  max={20}
                  step="0.01"
                />
                <Input label="Position" name="position" type="number" defaultValue={0} />
                <Button
                  type="submit"
                  size="sm"
                  loading={busyAction === "condition-create"}
                  disabled={busyAction !== null && busyAction !== "condition-create"}
                  leftIcon={<Plus className="h-4 w-4" />}
                >
                  Ajouter une condition
                </Button>
              </form>

              {conditions?.length === 0 && (
                <p className="text-sm text-text-muted">Aucune condition d’admission enregistrée.</p>
              )}
              <div className="space-y-3">
                {conditions?.map((condition) => (
                  <details key={condition.id} className="rounded-lg border border-border p-4">
                    <summary className="cursor-pointer font-semibold text-navy-800">
                      {condition.title}
                      <span className="ml-2 text-xs font-normal text-text-muted">
                        Position {condition.position}
                      </span>
                    </summary>
                    <form
                      onSubmit={(event) => void handleConditionUpdate(event, condition)}
                      className="mt-4 grid gap-3"
                    >
                      <Input label="Titre" name="title" defaultValue={condition.title} maxLength={200} required />
                      <Textarea label="Description" name="description" defaultValue={condition.description} />
                      <Input
                        label="Diplôme requis"
                        name="required_diploma"
                        defaultValue={condition.required_diploma ?? ""}
                        maxLength={120}
                      />
                      <Input
                        label="Moyenne minimale"
                        name="min_average"
                        type="number"
                        min={0}
                        max={20}
                        step="0.01"
                        defaultValue={condition.min_average ?? ""}
                      />
                      <Input label="Position" name="position" type="number" defaultValue={condition.position} />
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="submit"
                          size="sm"
                          loading={busyAction === `condition-${condition.id}`}
                          disabled={busyAction !== null && busyAction !== `condition-${condition.id}`}
                        >
                          Enregistrer
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="danger"
                          disabled={busyAction !== null}
                          onClick={() => void handleConditionDelete(condition)}
                          leftIcon={<Trash2 className="h-4 w-4" />}
                        >
                          Supprimer
                        </Button>
                      </div>
                    </form>
                  </details>
                ))}
              </div>
            </Card>

            <Card>
              <h2 className="mb-4 text-lg font-bold text-navy-800">Tarifs</h2>
              <form onSubmit={handleCreateTariff} className="mb-6 grid gap-3 border-b border-border pb-6">
                <Input
                  label="Année académique"
                  name="academic_year"
                  pattern="\d{4}-\d{4}"
                  placeholder="2026-2027"
                  required
                />
                <Input label="Montant" name="amount" type="number" min={0} step="0.01" required />
                <Input label="Frais d’inscription" name="registration_fee" type="number" min={0} step="0.01" />
                <Input label="Devise" name="currency" defaultValue="TND" minLength={3} maxLength={3} required />
                <Textarea label="Modalités de paiement" name="payment_terms" />
                <Button
                  type="submit"
                  size="sm"
                  loading={busyAction === "tariff-create"}
                  disabled={busyAction !== null && busyAction !== "tariff-create"}
                  leftIcon={<Plus className="h-4 w-4" />}
                >
                  Ajouter un tarif
                </Button>
              </form>

              {tariffs?.length === 0 && (
                <p className="text-sm text-text-muted">Aucun tarif enregistré.</p>
              )}
              <div className="space-y-3">
                {tariffs?.map((tariff) => (
                  <details key={tariff.id} className="rounded-lg border border-border p-4">
                    <summary className="cursor-pointer font-semibold text-navy-800">
                      {tariff.academic_year} · {tariff.amount} {tariff.currency}
                    </summary>
                    <form
                      onSubmit={(event) => void handleTariffUpdate(event, tariff)}
                      className="mt-4 grid gap-3"
                    >
                      <Input
                        label="Montant"
                        name="amount"
                        type="number"
                        min={0}
                        step="0.01"
                        defaultValue={tariff.amount}
                        required
                      />
                      <Input
                        label="Frais d’inscription"
                        name="registration_fee"
                        type="number"
                        min={0}
                        step="0.01"
                        defaultValue={tariff.registration_fee ?? ""}
                      />
                      <Input
                        label="Devise"
                        name="currency"
                        defaultValue={tariff.currency}
                        minLength={3}
                        maxLength={3}
                        required
                      />
                      <Textarea
                        label="Modalités de paiement"
                        name="payment_terms"
                        defaultValue={tariff.payment_terms ?? ""}
                      />
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="submit"
                          size="sm"
                          loading={busyAction === `tariff-${tariff.id}`}
                          disabled={busyAction !== null && busyAction !== `tariff-${tariff.id}`}
                        >
                          Enregistrer
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="danger"
                          disabled={busyAction !== null}
                          onClick={() => void handleTariffDelete(tariff)}
                          leftIcon={<Trash2 className="h-4 w-4" />}
                        >
                          Supprimer
                        </Button>
                      </div>
                    </form>
                  </details>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
