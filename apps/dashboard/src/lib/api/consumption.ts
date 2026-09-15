import { READINGS_ENDPOINT, READINGS_LIMIT } from "@/config/api";
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

export async function getConsumptionReadings(
  siteId: string,
): Promise<ConsumptionReading[]> {
  const { data } = await apiClient.get<ApiConsumptionReading[]>(
    READINGS_ENDPOINT,
    {
      params: {
        site_id: siteId,
        limit: READINGS_LIMIT,
      },
    },
  );

  return data.map(mapReading);
}
