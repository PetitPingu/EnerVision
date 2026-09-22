export type DriftStatus = "stable" | "moderate" | "critical" | "unknown";

export type ModelDrift = {
  site_id: string;
  drift_score: number | null;
  status: DriftStatus;
  mae_24h_kwh: number | null;
  mae_7d_kwh: number | null;
  /** MAE historique par tranche d'horizon (ex. "0-1h", "1-3j"), voir horizonBuckets.ts. */
  mae_by_horizon: Record<string, number>;
};
