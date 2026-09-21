"""Registre Prometheus des métriques de santé du modèle (docs/monitoring_model.md).

Un process léger : pas de framework HTTP, juste
`prometheus_client.start_http_server` en plus du scheduler APScheduler
(voir main.py) — même conteneur, même port exposé une seule fois au
démarrage du worker.
"""

from prometheus_client import Gauge, start_http_server

ml_prediction_mae_24h = Gauge(
    "ml_prediction_mae_24h",
    "MAE glissante sur 24h entre prédiction et mesure réelle, par site",
    ["site"],
)

ml_prediction_mae_7d = Gauge(
    "ml_prediction_mae_7d",
    "MAE glissante sur 7 jours entre prédiction et mesure réelle, par site",
    ["site"],
)

ml_feature_drift_score = Gauge(
    "ml_feature_drift_score",
    "Score de drift de la distribution de consumption_kwh vs la fenêtre d'entraînement, par site",
    ["site"],
)

ml_model_version = Gauge(
    "ml_model_version",
    "Vaut 1 pour la version de modèle actuellement observée sur un site",
    ["site", "version"],
)

ml_prediction_mae_by_horizon = Gauge(
    "ml_prediction_mae_by_horizon",
    "MAE historique par tranche d'horizon de prévision (target_timestamp - generated_at), par site",
    ["site", "horizon_bucket"],
)


def start_metrics_server(port: int) -> None:
    """Démarre le serveur HTTP /metrics (appelé une fois, au démarrage du worker)."""
    start_http_server(port)


def publish_model_health(
    mae_by_site: dict[str, float],
    drift_by_site: dict[str, float],
    model_version_by_site: dict[str, str],
    mae_by_horizon_by_site: dict[str, dict[str, float]] | None = None,
    mae_7d_by_site: dict[str, float] | None = None,
) -> None:
    """Met à jour les gauges Prometheus pour le cycle courant du job.

    Ne fait aucune remise à zéro des sites absents de ce cycle (une
    mesure Prometheus gardée à sa dernière valeur connue est un
    comportement standard et préférable à une chute artificielle à 0,
    qui se lirait comme "MAE nulle" plutôt que "pas de nouvelle donnée").
    """
    for site, mae in mae_by_site.items():
        ml_prediction_mae_24h.labels(site=site).set(mae)

    for site, mae in (mae_7d_by_site or {}).items():
        ml_prediction_mae_7d.labels(site=site).set(mae)

    for site, score in drift_by_site.items():
        ml_feature_drift_score.labels(site=site).set(score)

    for site, version in model_version_by_site.items():
        ml_model_version.labels(site=site, version=version).set(1)

    for site, mae_by_bucket in (mae_by_horizon_by_site or {}).items():
        for bucket, mae in mae_by_bucket.items():
            ml_prediction_mae_by_horizon.labels(site=site, horizon_bucket=bucket).set(mae)
