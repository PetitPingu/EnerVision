"use client";

import { EmptyState } from "@/components/EmptyState";
import { SiteCard } from "@/components/features/sites/SiteCard";
import { SitesSummaryCards } from "@/components/features/sites/SitesSummaryCards";
import { useSiteSelection } from "@/contexts/SiteSelectionContext";
import { useSensorsStatus } from "@/hooks/sites/useSensorsStatus";

function formatUpdatedAt(date: Date): string {
  return date.toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function SitesScreen() {
  const { sites, isLoading: isSitesLoading, error: sitesError } = useSiteSelection();
  const {
    data: sensorsStatus,
    isLoading: isStatusLoading,
    lastUpdatedAt,
  } = useSensorsStatus();

  const isLoading = isSitesLoading || isStatusLoading;

  // Total on/off des capteurs, tous sites confondus (pas un mélange de
  // compteurs de nature différente : capteurs vs sites, voir historique).
  let sensorsOnCount = 0;
  let sensorsOffCount = 0;

  for (const site of sites) {
    const sensors = Object.values(sensorsStatus[site.site_id]?.sensors ?? {});
    for (const sensor of sensors) {
      if (sensor.status === "failing") {
        sensorsOffCount += 1;
      } else {
        sensorsOnCount += 1;
      }
    }
  }

  return (
    <main className="flex-1 px-6 py-8 lg:px-10 lg:py-10">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-zinc-500">
          Cliquez sur un site pour voir son alerte et l&apos;estimation d&apos;état
          des capteurs à 24h.
        </p>
        {lastUpdatedAt && (
          <p className="text-xs text-zinc-400">
            Dernière actualisation : {formatUpdatedAt(lastUpdatedAt)}
          </p>
        )}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {[0, 1].map((key) => (
            <div key={key} className="h-28 animate-pulse rounded-2xl bg-zinc-100" />
          ))}
        </div>
      ) : sitesError ? (
        <p className="text-sm text-red-600">Impossible de charger les sites.</p>
      ) : (
        <SitesSummaryCards
          sitesCount={sites.length}
          sensorsOnCount={sensorsOnCount}
          sensorsOffCount={sensorsOffCount}
        />
      )}

      <div className="mt-6">
        {isLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2, 3, 4, 5].map((key) => (
              <div key={key} className="h-32 animate-pulse rounded-2xl bg-zinc-100" />
            ))}
          </div>
        ) : sites.length === 0 ? (
          <EmptyState message="Aucun site suivi" />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sites.map((site) => (
              <SiteCard
                key={site.site_id}
                site={site}
                status={sensorsStatus[site.site_id]}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
