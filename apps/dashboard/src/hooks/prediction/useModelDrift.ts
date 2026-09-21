"use client";

import { useEffect, useState } from "react";
import { getModelDrift } from "@/lib/api/model-health";
import type { ModelDrift } from "@/types/model-health";

// ModelHealthJob (etl_worker) tourne toutes les heures : un poll toutes les
// 5 minutes suffit à refléter un changement de statut sans solliciter
// Prometheus inutilement.
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

export function useModelDrift(siteId: string): ModelDrift | null {
  const [drift, setDrift] = useState<ModelDrift | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchDrift() {
      try {
        const result = await getModelDrift(siteId);
        if (!cancelled) {
          setDrift(result);
        }
      } catch {
        // Le badge de drift est une info secondaire : une erreur ne doit
        // pas empêcher le reste de la page de s'afficher.
        if (!cancelled) {
          setDrift(null);
        }
      }
    }

    fetchDrift();
    const interval = setInterval(fetchDrift, REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [siteId]);

  return drift;
}
