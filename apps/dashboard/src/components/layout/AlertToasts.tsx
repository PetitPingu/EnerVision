"use client";

import { useAlertStreamContext } from "@/contexts/AlertStreamContext";

// Un toast par retour à la normale, en plus (pas à la place) de l'entrée
// "Résolu" conservée dans la cloche : le toast donne l'info tout de suite,
// la cloche garde l'historique.
export function AlertToasts() {
  const { toasts, dismissToast } = useAlertStreamContext();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex w-80 flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 shadow-lg"
          style={{ boxShadow: "var(--card-shadow)" }}
        >
          <svg
            className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75l2.25 2.25 6-6" />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 12a9 9 0 11-9-9 9 9 0 019 9z"
            />
          </svg>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-emerald-900">{toast.siteId}</p>
            <p className="text-xs text-emerald-700">Retour à la normale</p>
          </div>
          <button
            type="button"
            aria-label="Fermer"
            onClick={() => dismissToast(toast.id)}
            className="shrink-0 text-emerald-500 hover:text-emerald-700"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
