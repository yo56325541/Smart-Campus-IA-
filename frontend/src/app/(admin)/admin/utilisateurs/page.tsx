"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Search, UserPlus, Users } from "lucide-react";
import { AdminPageHeader } from "@/components/admin/AdminPageHeader";
import { useCampus } from "@/components/providers/CampusProvider";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Input";
import {
  CampusApiError,
  createAdminUser,
  getAdminUsers,
  setAdminUserActive,
} from "@/lib/api/campus";
import type { AdminCreateUserIn, Role, UserOut } from "@/lib/types";

function formatCreatedAt(value: string | null) {
  if (!value) return "Date non renseignée";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(
    new Date(value),
  );
}

export default function AdminUsersPage() {
  const { accessToken, user: currentUser } = useCampus();
  const [users, setUsers] = useState<UserOut[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<Role>("candidat");
  const [creating, setCreating] = useState(false);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    if (!accessToken) {
      throw new Error("La session administrateur est absente. Reconnectez-vous.");
    }
    return getAdminUsers(accessToken);
  }, [accessToken]);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setUsers(await fetchUsers());
    } catch (requestError) {
      setError(
        requestError instanceof CampusApiError || requestError instanceof Error
          ? requestError.message
          : "Impossible de charger les comptes utilisateurs.",
      );
      setUsers(null);
    } finally {
      setLoading(false);
    }
  }, [fetchUsers]);

  useEffect(() => {
    let active = true;
    void Promise.resolve()
      .then(fetchUsers)
      .then((result) => {
        if (active) setUsers(result);
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        setError(
          requestError instanceof CampusApiError || requestError instanceof Error
            ? requestError.message
            : "Impossible de charger les comptes utilisateurs.",
        );
        setUsers(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fetchUsers]);

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("fr");
    if (!users || !query) return users ?? [];
    return users.filter((item) =>
      [item.full_name, item.email, item.role]
        .join(" ")
        .toLocaleLowerCase("fr")
        .includes(query),
    );
  }, [search, users]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) {
      setError("La session administrateur est absente. Reconnectez-vous.");
      return;
    }
    const form = event.currentTarget;
    const values = new FormData(form);
    const body: AdminCreateUserIn = {
      full_name: String(values.get("full_name") ?? "").trim(),
      email: String(values.get("email") ?? "").trim(),
      password: String(values.get("password") ?? ""),
      role,
    };

    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      const created = await createAdminUser(body, accessToken);
      setUsers((current) => [created, ...(current ?? [])].slice(0, 200));
      setSuccess(`Le compte ${created.email} a été créé.`);
      form.reset();
      setRole("candidat");
    } catch (requestError) {
      setError(
        requestError instanceof CampusApiError
          ? requestError.message
          : "La création du compte a échoué.",
      );
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(target: UserOut) {
    if (!accessToken) {
      setError("La session administrateur est absente. Reconnectez-vous.");
      return;
    }
    setUpdatingUserId(target.id);
    setError(null);
    setSuccess(null);
    try {
      const updated = await setAdminUserActive(
        target.id,
        { is_active: !target.is_active },
        accessToken,
      );
      setUsers((current) =>
        current?.map((item) => (item.id === updated.id ? updated : item)) ?? [],
      );
      setSuccess(
        updated.is_active
          ? `Le compte ${updated.email} est actif.`
          : `Le compte ${updated.email} a été désactivé.`,
      );
    } catch (requestError) {
      setError(
        requestError instanceof CampusApiError
          ? requestError.message
          : "La mise à jour du compte a échoué.",
      );
    } finally {
      setUpdatingUserId(null);
    }
  }

  return (
    <div className="animate-fade-in">
      <AdminPageHeader
        title="Gestion des utilisateurs"
        description="Comptes retournés par l’API administrateur. Les comptes visibles peuvent être créés, activés ou désactivés selon les règles Backend."
        icon={Users}
      />

      {error && (
        <Alert variant="error" title="Action impossible" className="mb-5">
          <p>{error}</p>
          {users === null && (
            <Button className="mt-3" size="sm" onClick={() => void loadUsers()}>
              Réessayer
            </Button>
          )}
        </Alert>
      )}
      {success && (
        <Alert variant="success" title="Mise à jour effectuée" className="mb-5">
          {success}
        </Alert>
      )}

      <div className="mb-8 grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.8fr)]">
        <Card>
          <div className="mb-5 flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-turquoise-700" aria-hidden="true" />
            <h2 className="text-lg font-bold text-navy-800">Créer un compte</h2>
          </div>
          <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Nom complet"
              name="full_name"
              maxLength={120}
              autoComplete="name"
              className="sm:col-span-2"
            />
            <Input
              label="Adresse e-mail"
              name="email"
              type="email"
              maxLength={255}
              autoComplete="email"
              required
            />
            <Input
              label="Mot de passe temporaire"
              name="password"
              type="password"
              minLength={8}
              maxLength={128}
              autoComplete="new-password"
              hint="8 à 128 caractères."
              required
            />
            <Select
              label="Rôle Backend"
              value={role}
              onChange={(event) => setRole(event.target.value as Role)}
            >
              <option value="candidat">Candidat</option>
              <option value="admin">Administrateur</option>
            </Select>
            <div className="flex items-end sm:col-span-2">
              <Button type="submit" loading={creating} leftIcon={<UserPlus className="h-4 w-4" />}>
                Créer le compte
              </Button>
            </div>
          </form>
        </Card>

        <Card className="bg-navy-800 text-white">
          <Badge variant="secondary" className="mb-4">Accès protégé</Badge>
          <h2 className="text-lg font-bold">Règles appliquées par le Backend</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-navy-100">
            <li>Seul un administrateur authentifié peut lire et gérer ces comptes.</li>
            <li>Un administrateur ne peut pas désactiver son propre compte.</li>
            <li>Le dernier administrateur actif ne peut pas être désactivé.</li>
          </ul>
        </Card>
      </div>

      <Card noPadding>
        <div className="flex flex-col gap-4 border-b border-border p-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-bold text-navy-800">Comptes enregistrés</h2>
            <p className="mt-1 text-sm text-text-muted">
              {users?.length === 200
                ? "Les 200 comptes les plus récents sont chargés."
                : users
                  ? `${users.length} compte${users.length === 1 ? "" : "s"} chargé${users.length === 1 ? "" : "s"}.`
                  : "Chargement des comptes…"}
            </p>
          </div>
          <div className="w-full sm:max-w-xs">
            <Input
              label="Filtrer les résultats chargés"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Nom, e-mail ou rôle"
              leftIcon={<Search className="h-4 w-4" />}
            />
          </div>
        </div>

        {loading && (
          <div className="space-y-3 p-5" aria-live="polite">
            <div className="h-10 animate-pulse rounded-lg bg-navy-50" />
            <div className="h-10 animate-pulse rounded-lg bg-navy-50" />
          </div>
        )}

        {!loading && users?.length === 0 && (
          <p className="p-8 text-center text-sm text-text-muted">
            Aucun compte utilisateur n’est disponible.
          </p>
        )}

        {!loading && users && users.length > 0 && filteredUsers.length === 0 && (
          <p className="p-8 text-center text-sm text-text-muted">
            Aucun compte chargé ne correspond à cette recherche.
          </p>
        )}

        {!loading && filteredUsers.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-navy-50 text-xs uppercase tracking-wide text-navy-700">
                <tr>
                  <th scope="col" className="px-5 py-3">Utilisateur</th>
                  <th scope="col" className="px-5 py-3">Rôle</th>
                  <th scope="col" className="px-5 py-3">Créé le</th>
                  <th scope="col" className="px-5 py-3">État</th>
                  <th scope="col" className="px-5 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredUsers.map((item) => {
                  const isCurrentUser = item.id === currentUser?.id;
                  return (
                    <tr key={item.id} className="align-middle">
                      <td className="px-5 py-4">
                        <p className="font-semibold text-navy-800">
                          {item.full_name || "Nom non renseigné"}
                        </p>
                        <p className="mt-1 text-xs text-text-muted">{item.email}</p>
                      </td>
                      <td className="px-5 py-4">
                        <Badge variant={item.role === "admin" ? "primary" : "outline"}>
                          {item.role === "admin" ? "Administrateur" : "Candidat"}
                        </Badge>
                      </td>
                      <td className="px-5 py-4 text-text-muted">
                        {formatCreatedAt(item.created_at)}
                      </td>
                      <td className="px-5 py-4">
                        <Badge variant={item.is_active ? "success" : "default"} dot>
                          {item.is_active ? "Actif" : "Inactif"}
                        </Badge>
                        {isCurrentUser && (
                          <span className="ml-2 text-xs text-text-muted">Vous</span>
                        )}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <Button
                          type="button"
                          size="sm"
                          variant={item.is_active ? "outline" : "secondary"}
                          disabled={isCurrentUser || updatingUserId !== null}
                          loading={updatingUserId === item.id}
                          onClick={() => void toggleActive(item)}
                          title={isCurrentUser ? "Le Backend interdit l’auto-désactivation." : undefined}
                        >
                          {item.is_active ? "Désactiver" : "Activer"}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
