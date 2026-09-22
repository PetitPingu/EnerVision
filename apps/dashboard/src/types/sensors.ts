export type SensorOnOffState = "on" | "off";

/** État prédit d'un capteur + confiance du modèle (probabilité de la
 * classe prédite, entre 0 et 1 — pas un intervalle de confiance
 * statistique), voir apps/prediction/infrastructure/ml/state/pipeline.py
 * (predict_with_confidence). */
export type SensorPrediction = {
  state: SensorOnOffState;
  confidence: number;
};

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
  sensors: Record<string, SensorPrediction>;
  model_version: string;
};

/** Un point de GET /api/v1/predictions/sensors/range (une heure). */
export type SensorStateRangePoint = {
  target_timestamp: string;
  sensors: Record<string, SensorPrediction>;
};

/** Réponse de GET /api/v1/predictions/sensors/range : un point par heure,
 * de start_time + 1h à start_time + hours. */
export type SensorStateRangePrediction = {
  site_id: string;
  hours: number;
  model_version: string;
  points: SensorStateRangePoint[];
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
