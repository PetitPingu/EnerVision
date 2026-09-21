// Transition data_quality publiée par etl_worker sur Redis Streams
// (alert.detected) et relayée par core_api via SSE (GET /api/v1/alerts/stream).
export type AlertKind = "alert" | "minor_alert" | "recovery";

export type AlertEvent = {
  event_id: string;
  site_id: string;
  timestamp: string;
  data_quality: string;
  null_reasons: string[];
  kind: AlertKind;
};
