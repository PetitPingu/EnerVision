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

/**
 * Correspondance entre les catégories de types/sensorStatus.ts (état en
 * direct, renvoyées telles quelles par l'API mock : consumption/electrical/
 * temperature/humidity/network) et les mesures brutes de readings_curated
 * que le modèle d'état sait prédire (voir SENSOR_COLUMNS côté
 * apps/prediction/infrastructure/ml/state/features.py).
 *
 * "network" n'a pas d'équivalent dans readings_curated : aucun modèle ne le
 * prédit aujourd'hui, à ne pas inventer côté front.
 */
export const SENSOR_STATUS_TO_MODEL_SENSORS: Record<string, string[]> = {
  consumption: ["consumption_kw"],
  electrical: ["voltage_v", "current_a", "power_factor"],
  temperature: ["temperature_celsius"],
  humidity: ["humidity_percent"],
};
