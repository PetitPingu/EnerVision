"use client";

import { ConsumptionSection } from "@/components/features/consumption/ConsumptionSection";
import { useSiteSelection } from "@/contexts/SiteSelectionContext";
import { formatSiteSubtitle } from "@/lib/format/site";

export function DashboardHome() {
  const { selectedSiteId, selectedSite, isLoading } = useSiteSelection();

  return (
    <main className="flex-1 px-6 py-8 lg:px-10 lg:py-10">
      <p className="mb-6 text-sm text-zinc-500">
        {isLoading || !selectedSite
          ? "Chargement du site…"
          : formatSiteSubtitle(selectedSite)}
      </p>

      <ConsumptionSection siteId={selectedSiteId} />
    </main>
  );
}
