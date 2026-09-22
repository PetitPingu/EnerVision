import { SENSOR_STATUS_TO_MODEL_SENSORS } from "@/types/sensors";
import type { ConsumptionReading } from "@/types/consumption";

export type SensorCategoryStatus = "ok" | "failing";

const ALL_MODEL_SENSOR_KEYS: (keyof ConsumptionReading)[] = [
  "consumption_kw",
  "voltage_v",
  "current_a",
  "power_factor",
  "temperature_celsius",
  "humidity_percent",
];

/**
 * Dérive l'état on/off des 5 catégories affichées (consumption/electrical/
 * temperature/humidity/network) à partir de la dernière lecture de NOTRE
 * base (readings_curated, via GET /api/v1/sites/{site_id}/current) —
 * exactement ce qu'etl_worker y écrit chaque minute — plutôt que d'un appel
 * séparé à l'état "en direct" de l'API mock (GET /api/v1/sensors/status),
 * qui peut avoir évolué depuis notre dernière ingestion.
 *
 * "network" n'a pas de colonne dédiée dans readings_curated : une panne
 * réseau (null_reasons: ["network_loss"] côté mock) nullifie les 6
 * mesures d'un coup, c'est ce signal qu'on détecte ici plutôt que de se
 * fier au texte de null_reasons (pas de vocabulaire garanti stable, voir
 * "network_outage" dans les tests vs "network_loss" observé en réel).
 */
export function deriveSensorCategoryStatus(
  reading: ConsumptionReading | null,
): Record<string, SensorCategoryStatus> {
  if (!reading) {
    return {};
  }

  const isNull = (key: keyof ConsumptionReading) => reading[key] === null;
  const allSensorsNull = ALL_MODEL_SENSOR_KEYS.every(isNull);

  const status: Record<string, SensorCategoryStatus> = {
    network: allSensorsNull ? "failing" : "ok",
  };

  for (const [category, modelKeys] of Object.entries(SENSOR_STATUS_TO_MODEL_SENSORS)) {
    status[category] = modelKeys.some((key) => isNull(key as keyof ConsumptionReading))
      ? "failing"
      : "ok";
  }

  return status;
}
