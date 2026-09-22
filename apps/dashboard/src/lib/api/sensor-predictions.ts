import { PREDICTIONS_SENSORS_RANGE_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { SensorStateRangePrediction } from "@/types/sensors";

/** Relaie GET /api/v1/predictions/sensors/range : un point par heure, de
 * startTime + 1h à startTime + hours. */
export async function getSensorStateRangePrediction(
  siteId: string,
  startTime: string,
  hours: number = 24,
): Promise<SensorStateRangePrediction> {
  const { data } = await apiClient.get<SensorStateRangePrediction>(
    PREDICTIONS_SENSORS_RANGE_ENDPOINT,
    { params: { site_id: siteId, start_time: startTime, hours } },
  );

  return data;
}
