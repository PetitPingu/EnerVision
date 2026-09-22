export const LOGIN_ENDPOINT = "/auth/login";

export const SITES_ENDPOINT = "/api/v1/sites";

export const READINGS_ENDPOINT = "/api/v1/readings";

/** Dernière lecture connue de chaque site, depuis notre base
 * (readings_curated) — pas un relais de l'API mock, contrairement à
 * GET /api/v1/sites/{site_id}/current. */
export const READINGS_LATEST_ENDPOINT = "/api/v1/readings/latest";

/** Limite max supportée par core-api (cf. `list_readings`). */
export const READINGS_LIMIT = 1000;

export const PREDICTIONS_RANGE_ENDPOINT = "/api/v1/predictions/range";

export const RECOMMENDATIONS_ENDPOINT = "/api/v1/recommendations";

export const ADMIN_USERS_ENDPOINT = "/admin/users";

export const ALERTS_STREAM_ENDPOINT = "/api/v1/alerts/stream";

export const ALERTS_ACTIVE_ENDPOINT = "/api/v1/alerts/active";

export const PREDICTIONS_SENSORS_RANGE_ENDPOINT = "/api/v1/predictions/sensors/range";

export const MODEL_HEALTH_DRIFT_ENDPOINT = "/api/v1/model-health/drift";

export const SENSORS_STATUS_ENDPOINT = "/api/v1/sensors/status";
