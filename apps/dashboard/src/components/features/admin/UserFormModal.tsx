"use client";

import { isAxiosError } from "axios";
import { useState } from "react";
import type { Site } from "@/types/site";
import type { AdminUser } from "@/types/user";

const MIN_PASSWORD_LENGTH = 12;

function extractErrorMessage(error: unknown): string {
  if (isAxiosError<{ detail?: string }>(error) && error.response?.data?.detail) {
    return error.response.data.detail;
  }
  return "Une erreur est survenue. Vérifiez les informations saisies.";
}

const ROLES = [
  { value: "admin", label: "Admin" },
  { value: "viewer", label: "Lecture seule" },
];

export type UserFormValues = {
  email: string;
  password: string;
  role: string;
  site_ids: string[];
};

type UserFormModalProps = {
  mode: "create" | "edit";
  sites: Site[];
  initialUser?: AdminUser;
  onClose: () => void;
  onSubmit: (values: UserFormValues) => Promise<void>;
};

export function UserFormModal({
  mode,
  sites,
  initialUser,
  onClose,
  onSubmit,
}: UserFormModalProps) {
  const [email, setEmail] = useState(initialUser?.email ?? "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(initialUser?.role ?? "viewer");
  const [siteIds, setSiteIds] = useState<string[]>(initialUser?.site_ids ?? []);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function toggleSite(siteId: string) {
    setSiteIds((current) =>
      current.includes(siteId)
        ? current.filter((id) => id !== siteId)
        : [...current, siteId],
    );
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await onSubmit({ email, password, role, site_ids: siteIds });
      onClose();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 px-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={mode === "create" ? "Ajouter un utilisateur" : "Modifier l'utilisateur"}
        className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 shadow-lg"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-zinc-900">
          {mode === "create" ? "Ajouter un utilisateur" : "Modifier l'utilisateur"}
        </h2>

        <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="user-email" className="text-sm font-medium text-zinc-700">
              Email
            </label>
            <input
              id="user-email"
              type="email"
              required
              disabled={mode === "edit"}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="rounded-xl border border-zinc-200 px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-400 disabled:bg-zinc-50 disabled:text-zinc-500"
            />
          </div>

          {mode === "create" && (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="user-password" className="text-sm font-medium text-zinc-700">
                Mot de passe
              </label>
              <input
                id="user-password"
                type="password"
                required
                minLength={MIN_PASSWORD_LENGTH}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="rounded-xl border border-zinc-200 px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-400"
              />
              <p className="text-xs text-zinc-500">
                Au moins {MIN_PASSWORD_LENGTH} caractères. Privilégiez la longueur
                (ex: une phrase) plutôt que la complexité.
              </p>
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label htmlFor="user-role" className="text-sm font-medium text-zinc-700">
              Rôle
            </label>
            <select
              id="user-role"
              value={role}
              onChange={(event) => setRole(event.target.value)}
              className="rounded-xl border border-zinc-200 px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-400"
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-zinc-700">
              Sites autorisés
            </span>
            {role === "admin" ? (
              <p className="text-sm text-zinc-500">
                Un admin a accès à tous les sites automatiquement.
              </p>
            ) : (
              <div className="flex max-h-40 flex-col gap-1.5 overflow-y-auto rounded-xl border border-zinc-200 p-2">
                {sites.map((site) => (
                  <label
                    key={site.site_id}
                    className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-zinc-700 hover:bg-zinc-50"
                  >
                    <input
                      type="checkbox"
                      checked={siteIds.includes(site.site_id)}
                      onChange={() => toggleSite(site.site_id)}
                      className="rounded border-zinc-300"
                    />
                    {site.site_name ?? site.site_id}
                  </label>
                ))}
              </div>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="mt-1 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl px-4 py-2 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-60"
            >
              {isSubmitting ? "Enregistrement…" : "Enregistrer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
