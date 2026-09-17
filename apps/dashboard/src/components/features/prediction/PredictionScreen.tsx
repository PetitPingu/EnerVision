"use client";

import { PredictionKpiRow } from "@/components/features/prediction/PredictionKpiRow";
import { PredictionSection } from "@/components/features/prediction/PredictionSection";
import { useSiteSelection } from "@/contexts/SiteSelectionContext";

const SITE_TYPE_LABELS: Record<string, string> = {
  office: "Bureau",
  factory: "Usine",
  datacenter: "Data center",
  retail: "Commerce",
  hospital: "Hôpital",
};

function formatSiteSubtitle(site: {
  site_name: string | null;
  site_type: string | null;
  location: string | null;
}): string {
  const typeLabel =
    (site.site_type && SITE_TYPE_LABELS[site.site_type]) ?? site.site_type;

  if (site.site_name && typeLabel && site.location) {
    return `${site.site_name} — ${typeLabel} · ${site.location}`;
  }

  if (site.site_name && site.location) {
    return `${site.site_name} — ${site.location}`;
  }

  return site.site_name ?? "Site sélectionné";
}

export function PredictionScreen() {
  const { selectedSiteId, selectedSite, isLoading } = useSiteSelection();

  return (
    <main className="flex-1 px-6 py-8 lg:px-10 lg:py-10">
      <p className="mb-6 text-sm text-zinc-500">
        {isLoading || !selectedSite
          ? "Chargement du site…"
          : formatSiteSubtitle(selectedSite)}
      </p>

      <PredictionKpiRow />
      <PredictionSection siteId={selectedSiteId} />
    </main>
  );
}
