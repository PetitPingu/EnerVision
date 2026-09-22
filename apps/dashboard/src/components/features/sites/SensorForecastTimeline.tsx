"use client";

import { useState } from "react";
import { useSensorStateRangePrediction } from "@/hooks/prediction/useSensorStateRangePrediction";
import { SENSOR_STATUS_TO_MODEL_SENSORS } from "@/types/sensors";
import type { SensorOnOffState, SensorStateRangePoint } from "@/types/sensors";

const HOURS = 24;

type CombinedPoint = {
  hour: number;
  state: SensorOnOffState;
  /** Confiance retenue pour ce point : le pire des capteurs bruts combinés
   * (ex. "electrical" = tension + courant + facteur de puissance) — la
   * moins bonne confiance est celle qui doit gouverner l'affichage. */
  confidence: number;
};

/** Combine les mesures brutes du modèle qui composent une catégorie
 * affichée (ex. "electrical" = voltage_v + current_a + power_factor) :
 * off si au moins une est off, confiance = la plus basse des mesures
 * combinées. */
function combinePoint(point: SensorStateRangePoint, modelSensorKeys: string[]): CombinedPoint | null {
  const predictions = modelSensorKeys
    .map((key) => point.sensors[key])
    .filter((prediction): prediction is NonNullable<typeof prediction> => Boolean(prediction));

  if (predictions.length === 0) {
    return null;
  }

  const state: SensorOnOffState = predictions.some((p) => p.state === "off") ? "off" : "on";
  const confidence = Math.min(...predictions.map((p) => p.confidence));

  return { hour: 0, state, confidence };
}

type SensorForecastTimelineProps = {
  siteId: string;
  /** Clé de SENSOR_STATUS_TO_MODEL_SENSORS (consumption/electrical/temperature/humidity/network). */
  sensorCategory: string;
  sensorLabel: string;
  siteName: string;
};

export function SensorForecastTimeline({
  siteId,
  sensorCategory,
  sensorLabel,
  siteName,
}: SensorForecastTimelineProps) {
  const modelSensorKeys = SENSOR_STATUS_TO_MODEL_SENSORS[sensorCategory];
  // Figé au montage : recalculer new Date() à chaque rendu changerait la
  // dépendance de useSensorStateRangePrediction en continu et déclencherait
  // une boucle de requêtes (voir useEffect deps du hook).
  const [startTime] = useState(() => new Date().toISOString());
  const { data, isLoading, modelNotLoaded, error } = useSensorStateRangePrediction(
    modelSensorKeys ? siteId : "",
    startTime,
    HOURS,
  );

  if (!modelSensorKeys) {
    return (
      <div className="mt-3 border-t border-zinc-100 pt-3">
        <p className="text-xs text-zinc-400">
          Aucun modèle ne prédit l&apos;état du capteur {sensorLabel} pour {siteName} :
          cette mesure n&apos;existe pas dans les données d&apos;entraînement (readings_curated).
        </p>
      </div>
    );
  }

  const points: CombinedPoint[] = (data?.points ?? [])
    .map((point) => combinePoint(point, modelSensorKeys))
    .filter((point): point is CombinedPoint => point !== null)
    .map((point, index) => ({ ...point, hour: index + 1 }));

  const forecastAt24h = points.at(-1) ?? null;

  return (
    <div className="mt-3 border-t border-zinc-100 pt-3">
      <p className="text-xs font-medium text-zinc-500">
        Prédiction des états des capteurs · {sensorLabel} ({siteName}) — 24 prochaines heures
      </p>

      {isLoading ? (
        <div className="mt-2 h-16 animate-pulse rounded-lg bg-zinc-100" />
      ) : modelNotLoaded ? (
        <p className="mt-2 text-xs text-zinc-400">
          Aucun modèle d&apos;état des capteurs n&apos;a encore été entraîné.
        </p>
      ) : error || !forecastAt24h ? (
        <p className="mt-2 text-xs text-red-600">
          Impossible de charger la prédiction.
        </p>
      ) : (
        <>
          <div
            className={`mt-2 inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-medium ${
              forecastAt24h.state === "off"
                ? "bg-red-50 text-red-700"
                : "bg-emerald-50 text-emerald-700"
            }`}
          >
            Prévu à 24h : {forecastAt24h.state === "off" ? "En panne" : "En marche"}
          </div>

          <div className="mt-2 flex gap-0.5" aria-hidden="true">
            {points.map((point) => (
              <span
                key={point.hour}
                title={`H+${point.hour} : ${point.state === "off" ? "En panne" : "En marche"}`}
                className={`h-6 flex-1 rounded-sm ${
                  point.state === "off" ? "bg-red-500" : "bg-emerald-500"
                }`}
              />
            ))}
          </div>
          <div className="mt-1 flex justify-between text-[10px] text-zinc-400">
            <span>H+1</span>
            <span>H+24</span>
          </div>
        </>
      )}
    </div>
  );
}
