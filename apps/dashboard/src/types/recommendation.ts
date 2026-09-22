// Actions produites par le moteur de règles du service recommendation
// (apps/recommendation/application/rules_engine.py).
export type RecommendationAction =
  | "load_shifting"
  | "peak_shift"
  | "power_factor_compensation";

export type Recommendation = {
  site_id: string;
  action: RecommendationAction;
  justification: string;
  estimated_gain_kwh: number | null;
  prediction_id: string | null;
  model_version: string | null;
};
