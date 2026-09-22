export type SensorState = {
  status: "ok" | "failing" | string;
  failing_until: string | null;
};

export type SiteSensorStatus = {
  site_name?: string;
  sensors: Record<string, SensorState>;
  overall: "ok" | "degraded" | "critical" | string;
};

/** Clé = site_id (cf. GET /api/v1/sensors/status, relayé tel quel depuis l'API mock). */
export type SensorsStatusResponse = Record<string, SiteSensorStatus>;
