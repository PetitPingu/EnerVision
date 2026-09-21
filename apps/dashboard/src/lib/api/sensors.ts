import { SENSORS_STATUS_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { SensorsStatusResponse } from "@/types/sensorStatus";

export async function getSensorsStatus(): Promise<SensorsStatusResponse> {
  const { data } = await apiClient.get<SensorsStatusResponse>(SENSORS_STATUS_ENDPOINT);
  return data;
}
