import { PREDICTIONS_SENSORS_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { SensorStatePrediction } from "@/types/sensors";

/** Relaie GET /api/v1/predictions/sensors (proxy de GET /predict/state du
 * service prediction) — à ne pas confondre avec getSensorsStatus()
 * (lib/api/sensors.ts), qui lit l'état observé en direct. */
export async function getSensorStatePrediction(
  siteId: string,
  timestamp: string,
): Promise<SensorStatePrediction> {
  const { data } = await apiClient.get<SensorStatePrediction>(
    PREDICTIONS_SENSORS_ENDPOINT,
    { params: { site_id: siteId, timestamp } },
  );

  return data;
}
