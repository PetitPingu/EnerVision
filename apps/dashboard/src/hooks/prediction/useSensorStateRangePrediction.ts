"use client";

import { useEffect, useState } from "react";
import { getSensorStateRangePrediction } from "@/lib/api/sensor-predictions";
import type { SensorStateRangePrediction } from "@/types/sensors";

type UseSensorStateRangePredictionResult = {
  data: SensorStateRangePrediction | null;
  isLoading: boolean;
  /** true si le service prediction n'a encore aucun modèle d'état promu
   * (503 côté core_api) — distinct d'une simple panne (error). */
  modelNotLoaded: boolean;
  error: Error | null;
};

export function useSensorStateRangePrediction(
  /** Vide = pas d'appel (ex. capteur sans modèle prédictif côté front). */
  siteId: string,
  startTime: string,
  hours: number = 24,
): UseSensorStateRangePredictionResult {
  const [data, setData] = useState<SensorStateRangePrediction | null>(null);
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
        const result = await getSensorStateRangePrediction(siteId, startTime, hours);
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
  }, [siteId, startTime, hours]);

  return { data, isLoading, modelNotLoaded, error };
}
