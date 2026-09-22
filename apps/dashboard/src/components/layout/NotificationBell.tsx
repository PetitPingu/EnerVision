"use client";

import { useEffect, useRef, useState } from "react";
import { useAlertStreamContext } from "@/contexts/AlertStreamContext";
import type { StoredAlert } from "@/hooks/alerts/useAlertStream";

const QUALITY_STYLES: Record<string, string> = {
  critical: "bg-red-50 text-red-700",
  degraded: "bg-amber-50 text-amber-700",
  partial: "bg-blue-50 text-blue-700",
};

const QUALITY_LABELS: Record<string, string> = {
  critical: "Critique",
  degraded: "Dégradée",
  partial: "Mineure",
};

function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function AlertRow({ alert }: { alert: StoredAlert }) {
  return (
    <li className={`flex items-start justify-between gap-3 px-4 py-3 ${alert.resolved ? "opacity-60" : ""}`}>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-zinc-900">{alert.site_id}</p>
        {alert.null_reasons.length > 0 && (
          <p className="truncate text-xs text-zinc-500">
            {alert.null_reasons.join(", ")}
          </p>
        )}
        <p className="mt-1 text-xs text-zinc-400">{formatTimestamp(alert.timestamp)}</p>
        {alert.resolved && alert.resolvedAt && (
          <p className="text-xs text-emerald-600">Résolu à {formatTimestamp(alert.resolvedAt)}</p>
        )}
      </div>
      {alert.resolved ? (
        <span className="shrink-0 rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-500">
          Résolu
        </span>
      ) : (
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
            QUALITY_STYLES[alert.data_quality] ?? "bg-zinc-100 text-zinc-700"
          }`}
        >
          {QUALITY_LABELS[alert.data_quality] ?? alert.data_quality}
        </span>
      )}
    </li>
  );
}

export function NotificationBell() {
  const { activeAlerts, hasUnreadAlerts, markAllAsRead } = useAlertStreamContext();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  function toggleOpen() {
    // Ne pas appeler markAllAsRead() (setState d'un autre composant,
    // AlertStreamProvider) depuis l'intérieur d'un updater de setIsOpen —
    // React l'interdit désormais explicitement (setState pendant le rendu
    // d'un composant tiers). isOpen est lu directement depuis la closure,
    // pas besoin de la forme fonctionnelle ici.
    const next = !isOpen;
    setIsOpen(next);
    if (next) markAllAsRead();
  }

  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-label="Notifications"
        aria-expanded={isOpen}
        onClick={toggleOpen}
        className="relative flex h-11 w-11 items-center justify-center rounded-xl border border-zinc-200 bg-white text-zinc-700 transition-colors hover:bg-zinc-50"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.75}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
          />
        </svg>
        {hasUnreadAlerts && (
          <span
            className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-orange-500 ring-2 ring-white"
            aria-hidden="true"
          />
        )}
      </button>

      {isOpen && (
        <div
          className="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-zinc-200 bg-white shadow-lg"
          style={{ boxShadow: "var(--card-shadow)" }}
        >
          <p className="border-b border-zinc-100 px-4 py-3 text-sm font-semibold text-zinc-900">
            Alertes qualité des données
          </p>
          {activeAlerts.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-zinc-500">
              Aucune alerte active
            </p>
          ) : (
            <ul className="max-h-80 divide-y divide-zinc-100 overflow-y-auto">
              {activeAlerts.map((alert) => (
                <AlertRow key={alert.site_id} alert={alert} />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
