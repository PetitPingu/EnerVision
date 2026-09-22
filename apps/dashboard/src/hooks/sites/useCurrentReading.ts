"use client";

import { useEffect, useState } from "react";
import { getCurrentReading } from "@/lib/api/sites";
import type { ConsumptionReading } from "@/types/consumption";

type UseCurrentReadingResult = {
  data: ConsumptionReading | null;
  isLoading: boolean;
  error: Error | null;
};

/** Dernière lecture connue d'un site (data_quality inclus) — vide = pas
 * d'appel. */
export function useCurrentReading(siteId: string): UseCurrentReadingResult {
  const [data, setData] = useState<ConsumptionReading | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchReading() {
      if (!siteId) {
        setData(null);
        setError(null);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);

      try {
        const result = await getCurrentReading(siteId);
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (cancelled) {
          return;
        }
        setData(null);
        setError(err instanceof Error ? err : new Error("Erreur inconnue"));
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchReading();

    return () => {
      cancelled = true;
    };
  }, [siteId]);

  return { data, isLoading, error };
}
