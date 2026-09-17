export type PredictionPoint = {
  target_timestamp: string;
  predicted_consumption_kwh: number;
};

export type PredictionInterval = "minute" | "hour";

export type PredictionRange = {
  site_id: string;
  start_time: string;
  end_time: string;
  interval: PredictionInterval;
  model_version: string | null;
  count: number;
  predictions: PredictionPoint[];
};

export type ComparisonPeriod = "24h" | "7d";
