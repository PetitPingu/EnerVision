"use client";

import { useEffect, useState } from "react";
import { getConsumptionReadings } from "@/lib/api/consumption";
import type { ConsumptionReading } from "@/types/consumption";

type UseConsumptionReadingsResult = {
  data: ConsumptionReading[];
  isLoading: boolean;
  error: Error | null;
};

export function useConsumptionReadings(
  siteId: string,
): UseConsumptionReadingsResult {
  const [data, setData] = useState<ConsumptionReading[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchReadings() {
      setIsLoading(true);
      setError(null);

      try {
        const readings = await getConsumptionReadings(siteId);
        if (!cancelled) {
          setData(readings);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err : new Error("Erreur de chargement"),
          );
          setData([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchReadings();

    return () => {
      cancelled = true;
    };
  }, [siteId]);

  return { data, isLoading, error };
}
