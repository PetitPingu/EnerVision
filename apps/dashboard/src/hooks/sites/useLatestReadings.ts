"use client";

import { useEffect, useRef, useState } from "react";
import { getLatestReadings } from "@/lib/api/consumption";
import type { ConsumptionReading } from "@/types/consumption";

export type LatestReadingsBySite = Record<string, ConsumptionReading>;

/**
 * Même optimisation que useSensorsStatus (avant elle) : réutilise la
 * référence précédente pour les sites dont la lecture n'a pas changé, pour
 * que React.memo sur SiteCard évite un re-render inutile à chaque poll.
 */
function mergePreservingUnchanged(
  previous: LatestReadingsBySite,
  next: LatestReadingsBySite,
): LatestReadingsBySite {
  const merged: LatestReadingsBySite = {};
  for (const [siteId, nextReading] of Object.entries(next)) {
    const previousReading = previous[siteId];
    merged[siteId] =
      previousReading && isSameReading(previousReading, nextReading)
        ? previousReading
        : nextReading;
  }
  return merged;
}

function isSameReading(a: ConsumptionReading, b: ConsumptionReading): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

// etl_worker ingère toutes les 60s (voir docs/ingestion-worker.md) : 15s
// donne une mise à jour quasi temps réel sans repoller inutilement entre
// deux cycles d'ingestion.
const POLL_INTERVAL_MS = 15_000;

type UseLatestReadingsResult = {
  data: LatestReadingsBySite;
  isLoading: boolean;
  lastUpdatedAt: Date | null;
};

/** Dernière lecture connue de chaque site, depuis notre base — voir
 * GET /api/v1/readings/latest. */
export function useLatestReadings(): UseLatestReadingsResult {
  const [data, setData] = useState<LatestReadingsBySite>({});
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const previousRef = useRef<LatestReadingsBySite>({});

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const readings = await getLatestReadings();
        if (cancelled) {
          return;
        }
        const bySite: LatestReadingsBySite = {};
        for (const reading of readings) {
          bySite[reading.site_id] = reading;
        }
        const merged = mergePreservingUnchanged(previousRef.current, bySite);
        previousRef.current = merged;
        setData(merged);
        setLastUpdatedAt(new Date());
      } catch {
        // Best-effort : un poll raté n'efface pas les dernières données
        // connues, le suivant réessaiera.
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return { data, isLoading, lastUpdatedAt };
}
