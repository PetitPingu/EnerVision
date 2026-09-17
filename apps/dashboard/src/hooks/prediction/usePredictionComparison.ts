"use client";

import { useEffect, useState } from "react";
import { getConsumptionReadings } from "@/lib/api/consumption";
import { getPredictionRange } from "@/lib/api/prediction";
import type { ComparisonPeriod, PredictionInterval } from "@/types/prediction";
import type { ConsumptionReading } from "@/types/consumption";
import type { PredictionPoint } from "@/types/prediction";

export type ComparisonPoint = {
  bucket: string;
  label: string;
  actual_kw: number | null;
  predicted_kw: number | null;
};

type UsePredictionComparisonResult = {
  data: ComparisonPoint[];
  /**
   * Bucket (clé ISO, garantie unique) du point de jonction, pour la ligne
   * "Maintenant". On utilise volontairement le bucket et non le label
   * affiché : deux buckets distincts peuvent partager le même label (ex.
   * "00:00" en début et en fin de fenêtre 24h), et un axe recharts de type
   * catégorie ne sait pas positionner une ReferenceLine sur une valeur
   * dupliquée dans son domaine.
   */
  nowBucket: string | null;
  isLoading: boolean;
  error: Error | null;
};

type LabelStyle = "time" | "datetime";

const PERIOD_CONFIG: Record<
  ComparisonPeriod,
  {
    pastBuckets: number;
    futureBuckets: number;
    bucketMinutes: number;
    labelStyle: LabelStyle;
    // Intervalle demandé au service prediction : évite de faire tourner le
    // modèle minute par minute puis d'agréger côté client quand seule une
    // résolution plus grossière est affichée (ex. vue semaine).
    predictionInterval: PredictionInterval;
  }
> = {
  // 12h d'historique + 12h de projection, minute par minute.
  "24h": {
    pastBuckets: 12 * 60,
    futureBuckets: 12 * 60,
    bucketMinutes: 1,
    labelStyle: "time",
    predictionInterval: "minute",
  },
  // 3 jours d'historique + 4 jours de projection, heure par heure
  // (3*24 = 72 buckets passés, 4*24 = 96 buckets futurs).
  "7d": {
    pastBuckets: 3 * 24,
    futureBuckets: 4 * 24,
    bucketMinutes: 60,
    labelStyle: "datetime",
    predictionInterval: "hour",
  },
};

function startOfBucket(date: Date, bucketMinutes: number): Date {
  const start = new Date(date);
  const totalMinutes = start.getHours() * 60 + start.getMinutes();
  const flooredTotal = Math.floor(totalMinutes / bucketMinutes) * bucketMinutes;
  start.setHours(Math.floor(flooredTotal / 60), flooredTotal % 60, 0, 0);
  return start;
}

function bucketSpanMs(bucketMinutes: number): number {
  return bucketMinutes * 60 * 1000;
}

function bucketKey(timestamp: string, bucketMinutes: number): string {
  return startOfBucket(new Date(timestamp), bucketMinutes).toISOString();
}

function average(values: number[]): number | null {
  if (values.length === 0) {
    return null;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function bucketReadings(
  readings: ConsumptionReading[],
  bucketMinutes: number,
): Map<string, number[]> {
  const buckets = new Map<string, number[]>();
  for (const reading of readings) {
    if (reading.consumption_kw === null) {
      continue;
    }
    const key = bucketKey(reading.timestamp, bucketMinutes);
    const values = buckets.get(key) ?? [];
    values.push(reading.consumption_kw);
    buckets.set(key, values);
  }
  return buckets;
}

function bucketPredictions(
  points: PredictionPoint[],
  bucketMinutes: number,
): Map<string, number[]> {
  const buckets = new Map<string, number[]>();
  for (const point of points) {
    const key = bucketKey(point.target_timestamp, bucketMinutes);
    const values = buckets.get(key) ?? [];
    // Approximation : la prévision est exprimée en kWh par minute, on la
    // traite comme équivalente à une puissance moyenne en kW sur ce point.
    values.push(point.predicted_consumption_kwh);
    buckets.set(key, values);
  }
  return buckets;
}

function formatLabel(bucketIso: string, labelStyle: LabelStyle): string {
  const date = new Date(bucketIso);
  if (labelStyle === "datetime") {
    const day = date.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
    const hour = date.getHours().toString().padStart(2, "0");
    return `${day} ${hour}h`;
  }
  return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

export function usePredictionComparison(
  siteId: string,
  period: ComparisonPeriod,
): UsePredictionComparisonResult {
  const [data, setData] = useState<ComparisonPoint[]>([]);
  const [nowBucket, setNowBucket] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchComparison() {
      setIsLoading(true);
      setError(null);

      const { pastBuckets, futureBuckets, bucketMinutes, labelStyle, predictionInterval } =
        PERIOD_CONFIG[period];
      const spanMs = bucketSpanMs(bucketMinutes);
      // Le pivot est aligné sur le début du bucket courant : l'historique
      // s'arrête juste avant, la prévision reprend exactement à partir de
      // là, sans qu'un même bucket ne soit partagé entre les deux séries
      // (ce qui cassait la continuité de la courbe).
      const pivot = startOfBucket(new Date(), bucketMinutes);
      const pastStart = new Date(pivot.getTime() - pastBuckets * spanMs);
      const futureEnd = new Date(pivot.getTime() + futureBuckets * spanMs);

      try {
        const [readings, prediction] = await Promise.all([
          // API mock : historique jusqu'au pivot (exclu).
          getConsumptionReadings(siteId, {
            startTime: pastStart.toISOString(),
            endTime: pivot.toISOString(),
          }),
          // Projection : à partir du pivot (inclus).
          getPredictionRange(
            siteId,
            pivot.toISOString(),
            futureEnd.toISOString(),
            predictionInterval,
          ),
        ]);

        if (cancelled) {
          return;
        }

        const actualBuckets = bucketReadings(readings, bucketMinutes);
        const predictedBuckets = bucketPredictions(
          prediction.predictions,
          bucketMinutes,
        );

        const buckets = new Set<string>([
          ...actualBuckets.keys(),
          ...predictedBuckets.keys(),
        ]);

        const points: ComparisonPoint[] = Array.from(buckets)
          .sort()
          .map((bucket) => ({
            bucket,
            label: formatLabel(bucket, labelStyle),
            actual_kw: average(actualBuckets.get(bucket) ?? []),
            predicted_kw: average(predictedBuckets.get(bucket) ?? []),
          }));

        // Les deux séries n'ont aucun bucket en commun (l'historique s'arrête
        // juste avant le pivot, la prévision reprend pile à partir de là), donc
        // recharts ne trace aucun trait entre elles. On fait du dernier point
        // réel un point de jonction : il porte aussi une valeur "prévue" égale
        // à la valeur réelle, pour que la ligne pointillée reparte exactement
        // là où la ligne pleine s'arrête, sans coupure visuelle.
        const junctionIndex = points.findLastIndex(
          (point) => point.actual_kw !== null,
        );
        if (
          junctionIndex !== -1 &&
          points[junctionIndex].predicted_kw === null
        ) {
          points[junctionIndex] = {
            ...points[junctionIndex],
            predicted_kw: points[junctionIndex].actual_kw,
          };
        }

        setData(points);
        // "Maintenant" doit apparaître sur les deux vues (24h et 7 jours) :
        // si aucune donnée réelle n'existe pile à la jonction (fenêtre de
        // mesures incomplète), on retombe sur le pivot lui-même plutôt que
        // de masquer le repère.
        setNowBucket(
          junctionIndex !== -1 ? points[junctionIndex].bucket : pivot.toISOString(),
        );
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err : new Error("Erreur de chargement"),
          );
          setData([]);
          setNowBucket(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchComparison();

    return () => {
      cancelled = true;
    };
  }, [siteId, period]);

  return { data, nowBucket, isLoading, error };
}
