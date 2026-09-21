import { MODEL_HEALTH_DRIFT_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { ModelDrift } from "@/types/model-health";

export async function getModelDrift(siteId: string): Promise<ModelDrift> {
  const { data } = await apiClient.get<ModelDrift>(MODEL_HEALTH_DRIFT_ENDPOINT, {
    params: { site_id: siteId },
  });

  return data;
}
