"use client";

import { useEffect, useState } from "react";
import { getConsumptionReadings } from "@/lib/api/consumption";
import { useModelDrift } from "@/hooks/prediction/useModelDrift";
import type { ComparisonPeriod } from "@/types/prediction";

export type PredictionAccuracy = {
  /** MAE glissante (kWh) sur la période choisie — ml_prediction_mae_24h/_7d (docs/monitoring_model.md). */
  maeKw: number | null;
  /** maeKw rapportée à la consommation moyenne du site sur la même période. */
  errorPct: number | null;
  /** 100 - errorPct (borné à 0) : lecture "positive" de la même mesure. */
  accuracyPct: number | null;
};

const PERIOD_HOURS: Record<ComparisonPeriod, number> = {
  "24h": 24,
  "7d": 7 * 24,
};

/**
 * Combine la MAE glissante (24h ou 7j selon `period`, via useModelDrift,
 * Prometheus) et la consommation moyenne réelle du site sur la même période
 * (via /api/v1/readings) pour dériver un taux d'erreur et une "précision" —
 * remplace les valeurs mockées de PredictionKpiRow.
 */
export function usePredictionAccuracy(
  siteId: string,
  period: ComparisonPeriod,
): PredictionAccuracy {
  const drift = useModelDrift(siteId);
  const [avgConsumptionKw, setAvgConsumptionKw] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchAverage() {
      try {
        const end = new Date();
        const start = new Date(end.getTime() - PERIOD_HOURS[period] * 60 * 60 * 1000);
        const readings = await getConsumptionReadings(siteId, {
          startTime: start.toISOString(),
          endTime: end.toISOString(),
        });
        const values = readings
          .map((reading) => reading.consumption_kw)
          .filter((value): value is number => value !== null);

        if (!cancelled) {
          setAvgConsumptionKw(
            values.length > 0 ? values.reduce((sum, v) => sum + v, 0) / values.length : null,
          );
        }
      } catch {
        // KPI secondaire : une erreur ne doit pas casser le reste de la page.
        if (!cancelled) {
          setAvgConsumptionKw(null);
        }
      }
    }

    fetchAverage();

    return () => {
      cancelled = true;
    };
  }, [siteId, period]);

  const maeKw = (period === "24h" ? drift?.mae_24h_kwh : drift?.mae_7d_kwh) ?? null;
  const errorPct =
    maeKw !== null && avgConsumptionKw !== null && avgConsumptionKw > 0
      ? (maeKw / avgConsumptionKw) * 100
      : null;
  const accuracyPct = errorPct !== null ? Math.max(0, 100 - errorPct) : null;

  return { maeKw, errorPct, accuracyPct };
}
