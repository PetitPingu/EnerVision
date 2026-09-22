import { SITES_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { Site } from "@/types/site";

export async function getSites(): Promise<Site[]> {
  const { data } = await apiClient.get<Site[]>(SITES_ENDPOINT);
  return data;
}
