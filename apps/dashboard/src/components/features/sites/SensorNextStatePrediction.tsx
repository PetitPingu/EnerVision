"use client";

import { useSensorStatePrediction } from "@/hooks/prediction/useSensorStatePrediction";
import { SENSOR_STATUS_TO_MODEL_SENSORS } from "@/types/sensors";

const MODEL_SENSOR_LABELS: Record<string, string> = {
  consumption_kw: "Consommation",
  voltage_v: "Tension",
  current_a: "Courant",
  power_factor: "Facteur de puissance",
  temperature_celsius: "Température",
  humidity_percent: "Humidité",
};

/** Arrondit à l'heure suivante : horizon de prédiction par défaut. */
function nextHourIso(): string {
  const date = new Date();
  date.setMinutes(0, 0, 0);
  date.setHours(date.getHours() + 1);
  return date.toISOString();
}

type SensorNextStatePredictionProps = {
  siteId: string;
  /** Clé de types/sensorStatus.ts (consumption/electrical/temperature/humidity/network). */
  sensorCategory: string;
  sensorLabel: string;
  siteName: string;
};

export function SensorNextStatePrediction({
  siteId,
  sensorCategory,
  sensorLabel,
  siteName,
}: SensorNextStatePredictionProps) {
  const modelSensorKeys = SENSOR_STATUS_TO_MODEL_SENSORS[sensorCategory];
  const targetTimestamp = nextHourIso();
  const { data, isLoading, modelNotLoaded, error } = useSensorStatePrediction(
    // "network" (pas de modèle) n'a pas besoin d'appeler l'API — un
    // site_id vide court-circuite le fetch, voir useSensorStatePrediction.
    modelSensorKeys ? siteId : "",
    targetTimestamp,
  );

  const formattedTarget = new Date(targetTimestamp).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });

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

  return (
    <div className="mt-3 border-t border-zinc-100 pt-3">
      <p className="text-xs font-medium text-zinc-500">
        Prédiction · {sensorLabel} ({siteName}) — à {formattedTarget}
      </p>

      {isLoading ? (
        <div className="mt-2 h-6 w-32 animate-pulse rounded-lg bg-zinc-100" />
      ) : modelNotLoaded ? (
        <p className="mt-2 text-xs text-zinc-400">
          Aucun modèle d&apos;état des capteurs n&apos;a encore été entraîné.
        </p>
      ) : error ? (
        <p className="mt-2 text-xs text-red-600">
          Impossible de charger la prédiction.
        </p>
      ) : data ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {modelSensorKeys.map((key) => {
            const state = data.sensors[key];
            return (
              <span
                key={key}
                className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium ${
                  state === "off"
                    ? "bg-red-50 text-red-700"
                    : "bg-emerald-50 text-emerald-700"
                }`}
              >
                {MODEL_SENSOR_LABELS[key] ?? key} :{" "}
                {state === "off" ? "en panne" : state === "on" ? "en marche" : "inconnu"}
              </span>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
