import { READINGS_ENDPOINT, READINGS_LATEST_ENDPOINT, READINGS_LIMIT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { ConsumptionReading, DataQuality } from "@/types/consumption";

type ApiConsumptionReading = Omit<ConsumptionReading, "site_type" | "data_quality"> & {
  site_type: string | null;
  data_quality: string | null;
};

function mapReading(raw: ApiConsumptionReading): ConsumptionReading {
  return {
    ...raw,
    site_type: raw.site_type ?? "unknown",
    null_reasons: raw.null_reasons ?? [],
    data_quality: (raw.data_quality ?? "good") as DataQuality,
  };
}

type ReadingsRange = {
  startTime?: string;
  endTime?: string;
};

export async function getConsumptionReadings(
  siteId: string,
  range?: ReadingsRange,
): Promise<ConsumptionReading[]> {
  const { data } = await apiClient.get<ApiConsumptionReading[]>(
    READINGS_ENDPOINT,
    {
      params: {
        site_id: siteId,
        start_time: range?.startTime,
        end_time: range?.endTime,
        limit: READINGS_LIMIT,
      },
    },
  );

  return data.map(mapReading);
}

/** Relaie GET /api/v1/readings/latest : dernière lecture connue de chaque
 * site, depuis notre base (readings_curated) — pas un relais de l'API mock
 * (contrairement à un éventuel appel "current" par site). */
export async function getLatestReadings(): Promise<ConsumptionReading[]> {
  const { data } = await apiClient.get<ApiConsumptionReading[]>(READINGS_LATEST_ENDPOINT);
  return data.map(mapReading);
}
