"use client";

import { PredictionKpiRow } from "@/components/features/prediction/PredictionKpiRow";
import { PredictionSection } from "@/components/features/prediction/PredictionSection";
import { RecommendationsSection } from "@/components/features/prediction/RecommendationsSection";
import { SensorPredictionSection } from "@/components/features/prediction/SensorPredictionSection";
import { useSiteSelection } from "@/contexts/SiteSelectionContext";
import { formatSiteSubtitle } from "@/lib/format/site";

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
      <RecommendationsSection siteId={selectedSiteId} />

      <div className="mt-6">
        <SensorPredictionSection siteId={selectedSiteId} />
      </div>
    </main>
  );
}
