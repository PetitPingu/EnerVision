import { siteCurrentReadingEndpoint, SITES_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { ConsumptionReading, DataQuality } from "@/types/consumption";
import type { Site } from "@/types/site";

export async function getSites(): Promise<Site[]> {
  const { data } = await apiClient.get<Site[]>(SITES_ENDPOINT);
  return data;
}

type ApiConsumptionReading = Omit<ConsumptionReading, "site_type" | "data_quality"> & {
  site_type: string | null;
  data_quality: string | null;
};

/** Relaie GET /api/v1/sites/{site_id}/current : dernière mesure connue du
 * site, avec le vrai data_quality (good/partial/degraded/critical) — la
 * même valeur que celle stockée dans readings_curated, pas une sévérité
 * recalculée côté front. */
export async function getCurrentReading(siteId: string): Promise<ConsumptionReading> {
  const { data } = await apiClient.get<ApiConsumptionReading>(
    siteCurrentReadingEndpoint(siteId),
  );

  return {
    ...data,
    site_type: data.site_type ?? "unknown",
    null_reasons: data.null_reasons ?? [],
    data_quality: (data.data_quality ?? "good") as DataQuality,
  };
}
