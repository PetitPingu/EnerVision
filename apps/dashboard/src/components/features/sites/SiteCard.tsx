"use client";

import { memo, useState } from "react";
import { SiteSensorsModal } from "@/components/features/sites/SiteSensorsModal";
import { DATA_QUALITY_DOT_COLORS } from "@/lib/format/dataQuality";
import { SITE_TYPE_LABELS } from "@/lib/format/site";
import type { ConsumptionReading } from "@/types/consumption";
import type { Site } from "@/types/site";

function SeverityDot({ reading }: { reading: ConsumptionReading | undefined }) {
  const dataQuality = reading?.data_quality ?? "good";
  if (dataQuality === "good") {
    return null;
  }

  return (
    <div className="flex shrink-0 items-center gap-1" aria-hidden="true">
      <span className={`h-2 w-2 rounded-full ${DATA_QUALITY_DOT_COLORS[dataQuality]}`} />
    </div>
  );
}

type SiteCardProps = {
  site: Site;
  reading: ConsumptionReading | undefined;
};

/**
 * memo() + reading calculé côté parent (useLatestReadings ne change la
 * référence que pour les sites dont la lecture a réellement changé, cf.
 * mergePreservingUnchanged) : les cartes des sites inchangés ne se
 * re-rendent pas à chaque poll.
 */
export const SiteCard = memo(function SiteCard({ site, reading }: SiteCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

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
        <SeverityDot reading={reading} />
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
        <SiteSensorsModal
          site={site}
          reading={reading}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </div>
  );
});
