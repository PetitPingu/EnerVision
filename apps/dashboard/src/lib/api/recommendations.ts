import { RECOMMENDATIONS_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { Recommendation } from "@/types/recommendation";

export async function getRecommendations(
  siteId: string,
): Promise<Recommendation[]> {
  const { data } = await apiClient.get<Recommendation[]>(
    RECOMMENDATIONS_ENDPOINT,
    { params: { site_id: siteId } },
  );

  return data;
}
