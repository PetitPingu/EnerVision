"use client";

import { useEffect, useState } from "react";
import { getRecommendations } from "@/lib/api/recommendations";
import type { Recommendation } from "@/types/recommendation";

type UseRecommendationsResult = {
  data: Recommendation[];
  isLoading: boolean;
  error: Error | null;
};

export function useRecommendations(siteId: string): UseRecommendationsResult {
  const [data, setData] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchRecommendations() {
      setIsLoading(true);
      setError(null);

      try {
        const recommendations = await getRecommendations(siteId);
        if (!cancelled) {
          setData(recommendations);
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

    fetchRecommendations();

    return () => {
      cancelled = true;
    };
  }, [siteId]);

  return { data, isLoading, error };
}
