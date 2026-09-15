import type { ConsumptionReading } from "@/types/consumption";
import { SITE001_MOCK_READINGS } from "@/lib/api/mock/site001-consumption";

export async function getConsumptionReadings(
  siteId: string,
): Promise<ConsumptionReading[]> {
  // Branchement futur :
  // const { data } = await apiClient.get<ConsumptionReading[]>(
  //   `/sites/${siteId}/consumption`,
  // );
  // return data;

  if (siteId === "SITE001") {
    return SITE001_MOCK_READINGS;
  }
  return [];
}
