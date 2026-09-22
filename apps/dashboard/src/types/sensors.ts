export type SensorOnOffState = "on" | "off";

/**
 * Réponse de GET /api/v1/predictions/sensors (relais de
 * GET /predict/state côté service prediction) : état on/off *prédit* par
 * capteur, un capteur = une mesure de readings_curated. Pas d'état global
 * déduit (good/partial/degraded/critical) — voir
 * apps/prediction/docs/state-model.md.
 *
 * À ne pas confondre avec types/sensorStatus.ts (SensorsStatusResponse),
 * qui relaie l'état *observé en direct* des capteurs depuis l'API mock.
 */
export type SensorStatePrediction = {
  site_id: string;
  target_timestamp: string;
  sensors: Record<string, SensorOnOffState>;
  model_version: string;
};
