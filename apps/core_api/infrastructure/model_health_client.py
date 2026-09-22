"""Client HTTP pour la santé du modèle (drift + MAE, voir docs/monitoring_model.md).

Contrairement à prediction_client.py / recommendation_client.py, qui
relaient un service applicatif interne, celui-ci interroge directement
l'API HTTP de Prometheus : `ml_feature_drift_score` / `ml_prediction_mae_24h`
sont calculées par apps/etl_worker (ModelHealthJob) et ne vivent qu'en
mémoire dans ce process, scrapées par Prometheus — core_api n'a pas
d'autre moyen d'y accéder.
"""

import logging

import requests

from .config import Config

logger = logging.getLogger(__name__)


class ModelHealthClient:
    """Interroge Prometheus. Ne lève jamais d'exception : renvoie None si
    la métrique est absente (échantillon insuffisant côté ModelHealthJob,
    site jamais rapproché) ou si Prometheus est injoignable — les deux cas
    sont indiscernables depuis ici, et traités pareil côté endpoint
    (statut "unknown")."""

    def __init__(self, base_url: str = None, timeout: float = None):
        self._base_url = (base_url or Config.PROMETHEUS_URL).rstrip("/")
        self._timeout = timeout if timeout is not None else Config.REQUEST_TIMEOUT

    def get_drift_score(self, site_id: str) -> float | None:
        """Dernière valeur connue de ml_feature_drift_score{site=site_id}."""
        return self._query_instant(f'ml_feature_drift_score{{site="{site_id}"}}')

    def get_mae_24h(self, site_id: str) -> float | None:
        """Dernière valeur connue de ml_prediction_mae_24h{site=site_id} (kWh).

        Sert à dessiner une marge d'erreur empirique autour de la courbe de
        prévision côté dashboard (docs/monitoring_model.md) — pas un vrai
        intervalle de confiance statistique, juste "à quel point le modèle
        s'est trompé récemment sur ce site"."""
        return self._query_instant(f'ml_prediction_mae_24h{{site="{site_id}"}}')

    def get_mae_7d(self, site_id: str) -> float | None:
        """Dernière valeur connue de ml_prediction_mae_7d{site=site_id} (kWh)
        — même usage que get_mae_24h, pour la vue "7 jours" du dashboard."""
        return self._query_instant(f'ml_prediction_mae_7d{{site="{site_id}"}}')

    def get_mae_by_horizon(self, site_id: str) -> dict[str, float]:
        """MAE historique par tranche d'horizon pour ce site
        (ml_prediction_mae_by_horizon{site=site_id}), toutes tranches
        confondues en un seul appel. Sert à faire grandir la marge
        d'erreur du dashboard avec l'horizon de prévision au lieu d'une
        largeur constante (docs/monitoring_model.md). Dict vide si la
        métrique est absente ou Prometheus injoignable — jamais d'exception."""
        try:
            response = requests.get(
                f"{self._base_url}/api/v1/query",
                params={"query": f'ml_prediction_mae_by_horizon{{site="{site_id}"}}'},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Échec de l'appel à Prometheus (mae_by_horizon, %s) : %s", site_id, exc)
            return {}

        results = response.json().get("data", {}).get("result", [])
        return {
            row["metric"]["horizon_bucket"]: float(row["value"][1])
            for row in results
            if "horizon_bucket" in row.get("metric", {})
        }

    def _query_instant(self, query: str) -> float | None:
        try:
            response = requests.get(
                f"{self._base_url}/api/v1/query",
                params={"query": query},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Échec de l'appel à Prometheus (%s) : %s", query, exc)
            return None

        results = response.json().get("data", {}).get("result", [])
        if not results:
            return None

        _timestamp, value = results[0]["value"]
        return float(value)
