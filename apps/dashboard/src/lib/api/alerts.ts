import { ALERTS_ACTIVE_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { AlertEvent } from "@/types/alert";

export async function getActiveAlerts(): Promise<AlertEvent[]> {
  const { data } = await apiClient.get<AlertEvent[]>(ALERTS_ACTIVE_ENDPOINT);
  return data;
}
