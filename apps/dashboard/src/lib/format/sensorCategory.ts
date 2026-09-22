import { SENSOR_STATUS_TO_MODEL_SENSORS } from "@/types/sensors";
import type { ConsumptionReading } from "@/types/consumption";

export type SensorCategoryStatus = "ok" | "failing";

/**
 * Dérive l'état on/off des 4 catégories affichées (consumption/electrical/
 * temperature/humidity) à partir de la dernière lecture de NOTRE base
 * (readings_curated, via GET /api/v1/readings/latest) — exactement ce
 * qu'etl_worker y écrit chaque minute — plutôt que d'un appel séparé à
 * l'état "en direct" de l'API mock, qui peut avoir évolué depuis notre
 * dernière ingestion.
 *
 * Pas de catégorie "network" : aucune colonne dédiée dans readings_curated
 * (voir SENSOR_STATUS_TO_MODEL_SENSORS), rien de fiable à afficher.
 */
export function deriveSensorCategoryStatus(
  reading: ConsumptionReading | null,
): Record<string, SensorCategoryStatus> {
  if (!reading) {
    return {};
  }

  const isNull = (key: keyof ConsumptionReading) => reading[key] === null;
  const status: Record<string, SensorCategoryStatus> = {};

  for (const [category, modelKeys] of Object.entries(SENSOR_STATUS_TO_MODEL_SENSORS)) {
    status[category] = modelKeys.some((key) => isNull(key as keyof ConsumptionReading))
      ? "failing"
      : "ok";
  }

  return status;
}
