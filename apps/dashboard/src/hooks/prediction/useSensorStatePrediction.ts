"use client";

import { useEffect, useState } from "react";
import { getSensorStatePrediction } from "@/lib/api/sensor-predictions";
import type { SensorStatePrediction } from "@/types/sensors";

type UseSensorStatePredictionResult = {
  data: SensorStatePrediction | null;
  isLoading: boolean;
  /** true si le service prediction n'a encore aucun modèle d'état promu
   * (503 côté core_api) — distinct d'une simple panne (error). */
  modelNotLoaded: boolean;
  error: Error | null;
};

export function useSensorStatePrediction(
  /** Vide = pas d'appel (ex. capteur sans modèle prédictif côté front). */
  siteId: string,
  timestamp: string,
): UseSensorStatePredictionResult {
  const [data, setData] = useState<SensorStatePrediction | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [modelNotLoaded, setModelNotLoaded] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchPrediction() {
      if (!siteId) {
        setData(null);
        setModelNotLoaded(false);
        setError(null);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);

      try {
        const result = await getSensorStatePrediction(siteId, timestamp);
        if (!cancelled) {
          setData(result);
          setModelNotLoaded(false);
          setError(null);
        }
      } catch (err) {
        if (cancelled) {
          return;
        }
        setData(null);
        const status = (err as { response?: { status?: number } })?.response?.status;
        setModelNotLoaded(status === 503);
        setError(err instanceof Error ? err : new Error("Erreur inconnue"));
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchPrediction();

    return () => {
      cancelled = true;
    };
  }, [siteId, timestamp]);

  return { data, isLoading, modelNotLoaded, error };
}
