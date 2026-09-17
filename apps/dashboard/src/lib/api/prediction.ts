import { PREDICTIONS_RANGE_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { PredictionInterval, PredictionRange } from "@/types/prediction";

export async function getPredictionRange(
  siteId: string,
  startTime: string,
  endTime: string,
  interval: PredictionInterval = "minute",
): Promise<PredictionRange> {
  const { data } = await apiClient.get<PredictionRange>(
    PREDICTIONS_RANGE_ENDPOINT,
    {
      params: {
        site_id: siteId,
        start_time: startTime,
        end_time: endTime,
        interval,
      },
    },
  );

  return data;
}
