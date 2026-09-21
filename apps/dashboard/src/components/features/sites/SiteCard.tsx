"use client";

import { memo, useMemo, useState } from "react";
import { SiteSensorsModal } from "@/components/features/sites/SiteSensorsModal";
import { SITE_TYPE_LABELS } from "@/lib/format/site";
import type { Site } from "@/types/site";
import type { SiteSensorStatus } from "@/types/sensorStatus";

type SeverityFlags = {
  partiel: boolean;
  degrade: boolean;
  critique: boolean;
};

/**
 * Un capteur en panne compte pour "partiel" ; overall (calculé par l'API
 * mock à partir des capteurs en panne du site — "critical" dès que le
 * capteur "network" est en panne, "degraded" sinon) donne le badge
 * dégradé/critique. Un site peut donc afficher jusqu'à 2 pastilles.
 */
export function computeSeverity(status: SiteSensorStatus | undefined): SeverityFlags {
  if (!status) {
    return { partiel: false, degrade: false, critique: false };
  }

  const hasFailingSensor = Object.values(status.sensors).some(
    (sensor) => sensor.status === "failing",
  );

  return {
    partiel: hasFailingSensor,
    degrade: status.overall === "degraded",
    critique: status.overall === "critical",
  };
}

function SeverityDots({ severity }: { severity: SeverityFlags }) {
  if (!severity.partiel && !severity.degrade && !severity.critique) {
    return null;
  }

  return (
    <div className="flex shrink-0 items-center gap-1" aria-hidden="true">
      {severity.partiel && <span className="h-2 w-2 rounded-full bg-blue-500" />}
      {severity.degrade && <span className="h-2 w-2 rounded-full bg-amber-500" />}
      {severity.critique && <span className="h-2 w-2 rounded-full bg-red-500" />}
    </div>
  );
}

type SiteCardProps = {
  site: Site;
  status: SiteSensorStatus | undefined;
};

/**
 * memo() + status calculé en interne (plutôt que reçu en prop "severity"
 * recalculé à chaque render du parent) : useSensorsStatus ne change la
 * référence de `status` que pour les sites dont les données ont réellement
 * changé (cf. mergePreservingUnchanged), donc les cartes des sites inchangés
 * ne se re-rendent pas à chaque poll.
 */
export const SiteCard = memo(function SiteCard({ site, status }: SiteCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const severity = useMemo(() => computeSeverity(status), [status]);

  const typeLabel =
    (site.site_type && SITE_TYPE_LABELS[site.site_type]) ?? site.site_type;

  return (
    <div
      className="rounded-2xl bg-white p-5 shadow-sm"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-400">
          {site.site_id}
        </p>
        <SeverityDots severity={severity} />
      </div>

      <h3 className="mt-1 text-base font-semibold text-zinc-900">
        {site.site_name ?? site.site_id}
      </h3>

      {(typeLabel || site.location) && (
        <p className="mt-0.5 text-sm text-blue-600">
          {[typeLabel, site.location].filter(Boolean).join(" · ")}
        </p>
      )}

      <button
        type="button"
        onClick={() => setIsModalOpen(true)}
        className="mt-3 text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-900"
      >
        Voir l&apos;alerte et la prédiction →
      </button>

      {isModalOpen && (
        <SiteSensorsModal site={site} status={status} onClose={() => setIsModalOpen(false)} />
      )}
    </div>
  );
});
