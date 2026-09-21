"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { EmptyState } from "@/components/EmptyState";
import { UserFormModal, type UserFormValues } from "@/components/features/admin/UserFormModal";
import { useAuth } from "@/contexts/AuthContext";
import { createUser, deleteUser, listUsers, updateUser } from "@/lib/api/admin";
import { getSites } from "@/lib/api/sites";
import type { Site } from "@/types/site";
import type { AdminUser } from "@/types/user";

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  viewer: "Lecture seule",
};

type ModalState = { mode: "create" } | { mode: "edit"; user: AdminUser } | null;

export function AdminUsersScreen() {
  const router = useRouter();
  const { email: currentEmail, isAdmin, isLoading: isAuthLoading } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalState, setModalState] = useState<ModalState>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [usersData, sitesData] = await Promise.all([listUsers(), getSites()]);
      setUsers(usersData);
      setSites(sitesData);
    } catch {
      setError("Impossible de charger les utilisateurs.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    function runInitialLoad() {
      if (isAdmin) {
        load();
      }
    }

    runInitialLoad();
  }, [isAdmin, load]);

  // Un non-admin (ou un compte déconnecté) n'a rien à faire sur cette page
  // — le backend refuserait de toute façon toute requête /admin/* (403).
  useEffect(() => {
    if (!isAuthLoading && !isAdmin) {
      router.replace("/");
    }
  }, [isAuthLoading, isAdmin, router]);

  async function handleCreate(values: UserFormValues) {
    await createUser({
      email: values.email,
      password: values.password,
      role: values.role,
      site_ids: values.site_ids,
    });
    await load();
  }

  async function handleEdit(userId: string, values: UserFormValues) {
    await updateUser(userId, { role: values.role, site_ids: values.site_ids });
    await load();
  }

  async function handleDelete(user: AdminUser) {
    if (!window.confirm(`Supprimer ${user.email} ?`)) return;
    try {
      await deleteUser(user.id);
      await load();
    } catch {
      setError(`Impossible de supprimer ${user.email}.`);
    }
  }

  function siteLabel(siteId: string): string {
    return sites.find((site) => site.site_id === siteId)?.site_name ?? siteId;
  }

  if (!isAdmin) {
    return null;
  }

  return (
    <main className="flex-1 px-6 py-8 lg:px-10 lg:py-10">
      <div
        className="rounded-2xl bg-white p-8 shadow-sm"
        style={{ boxShadow: "var(--card-shadow)" }}
      >
        <div className="mb-6 flex items-center justify-between gap-4">
          <h2 className="text-xl font-semibold text-zinc-900">Utilisateurs</h2>
          <button
            type="button"
            onClick={() => setModalState({ mode: "create" })}
            className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800"
          >
            Ajouter un utilisateur
          </button>
        </div>

        {isLoading ? (
          <div className="flex flex-col gap-3">
            {[0, 1, 2].map((key) => (
              <div key={key} className="h-12 animate-pulse rounded-xl bg-zinc-50" />
            ))}
          </div>
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : users.length === 0 ? (
          <EmptyState message="Aucun utilisateur" />
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-zinc-500">
                <th className="py-2 font-medium">Email</th>
                <th className="py-2 font-medium">Rôle</th>
                <th className="py-2 font-medium">Sites</th>
                <th className="py-2 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const isSelf = user.email === currentEmail;
                return (
                  <tr key={user.id} className="border-b border-zinc-100 last:border-0">
                    <td className="py-3 text-zinc-900">
                      {user.email}
                      {isSelf && <span className="ml-2 text-xs text-zinc-400">(vous)</span>}
                    </td>
                    <td className="py-3 text-zinc-600">
                      {ROLE_LABELS[user.role ?? ""] ?? user.role ?? "-"}
                    </td>
                    <td className="py-3 text-zinc-600">
                      {user.role === "admin" ? (
                        <span className="text-zinc-400">Tous les sites</span>
                      ) : user.site_ids.length === 0 ? (
                        <span className="text-zinc-400">Aucun</span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {user.site_ids.map((siteId) => (
                            <span
                              key={siteId}
                              className="rounded-lg bg-zinc-100 px-2 py-0.5 text-xs text-zinc-700"
                            >
                              {siteLabel(siteId)}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        type="button"
                        onClick={() => setModalState({ mode: "edit", user })}
                        className="rounded-lg px-3 py-1.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100"
                      >
                        Modifier
                      </button>
                      <button
                        type="button"
                        disabled={isSelf}
                        onClick={() => handleDelete(user)}
                        title={
                          isSelf
                            ? "Vous ne pouvez pas supprimer votre propre compte"
                            : undefined
                        }
                        className="rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:text-zinc-300 disabled:hover:bg-transparent"
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {modalState?.mode === "create" && (
        <UserFormModal
          mode="create"
          sites={sites}
          onClose={() => setModalState(null)}
          onSubmit={handleCreate}
        />
      )}
      {modalState?.mode === "edit" && (
        <UserFormModal
          mode="edit"
          sites={sites}
          initialUser={modalState.user}
          onClose={() => setModalState(null)}
          onSubmit={(values) => handleEdit(modalState.user.id, values)}
        />
      )}
    </main>
  );
}
