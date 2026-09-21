"use client";

import { isAxiosError } from "axios";
import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

type LoginModalProps = {
  onClose: () => void;
};

function extractErrorMessage(error: unknown): string {
  if (isAxiosError<{ detail?: string }>(error) && error.response?.data?.detail) {
    return error.response.data.detail;
  }
  return "Identifiants invalides.";
}

export function LoginModal({ onClose }: LoginModalProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
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
        aria-label="Connexion"
        className="w-full max-w-sm rounded-2xl border border-zinc-200 bg-white p-6 shadow-lg"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-zinc-900">Connexion</h2>
        <p className="mt-1 text-sm text-zinc-500">
          Connectez-vous pour accéder au dashboard EnerVision.
        </p>

        <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="login-email" className="text-sm font-medium text-zinc-700">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              required
              autoFocus
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="rounded-xl border border-zinc-200 px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-400"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="login-password" className="text-sm font-medium text-zinc-700">
              Mot de passe
            </label>
            <input
              id="login-password"
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="rounded-xl border border-zinc-200 px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-400"
            />
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
              {isSubmitting ? "Connexion…" : "Se connecter"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
