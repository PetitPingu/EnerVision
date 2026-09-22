"""Client HTTP pour le service prediction (voir apps/prediction).

Relaie les prévisions de consommation vers le service interne `prediction`
(adressé via PREDICTION_URL). Ne lève jamais d'exception pour une panne
générique : les erreurs sont loggées et `None` est retourné à l'appelant,
qui traduit ça en 502. Exception : get_sensor_state() lève
PredictionModelNotLoadedError sur un 503 du service prediction ("aucun
modèle d'état promu"), à distinguer d'un service injoignable.
"""

import logging

import requests

from .config import Config

logger = logging.getLogger(__name__)


class PredictionModelNotLoadedError(Exception):
    """Le service prediction répond, mais aucun modèle d'état n'a encore
    été promu (503 sur /predict/state)."""


class PredictionApiClient:
    """Appelle le service prediction et ne lève jamais d'exception."""

    def __init__(self, base_url: str = None, timeout: float = None):
        self._base_url = (base_url or Config.PREDICTION_URL).rstrip("/")
        self._timeout = timeout if timeout is not None else Config.REQUEST_TIMEOUT

    def get_prediction_range(
        self,
        site_id: str,
        start_time: str,
        end_time: str,
        interval: str = "minute",
    ) -> dict | None:
        """Relaie GET /predict/range du service prediction."""
        try:
            response = requests.get(
                f"{self._base_url}/predict/range",
                params={
                    "site_id": site_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "interval": interval,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error(
                "Échec de l'appel au service prediction (predict/range, %s) : %s",
                site_id,
                exc,
            )
            return None

        return response.json()

    def get_sensor_state(self, site_id: str, timestamp: str) -> dict | None:
        """Relaie GET /predict/state du service prediction : état on/off
        prédit pour chacun des capteurs d'un site à un instant donné.

        Lève PredictionModelNotLoadedError sur un 503 (aucun modèle d'état
        promu) plutôt que de retourner None, pour que l'appelant distingue
        "pas encore de modèle" d'un service prediction injoignable.
        """
        try:
            response = requests.get(
                f"{self._base_url}/predict/state",
                params={"site_id": site_id, "timestamp": timestamp},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 503:
                raise PredictionModelNotLoadedError from exc
            logger.error(
                "Échec de l'appel au service prediction (predict/state, %s) : %s",
                site_id,
                exc,
            )
            return None
        except requests.RequestException as exc:
            logger.error(
                "Échec de l'appel au service prediction (predict/state, %s) : %s",
                site_id,
                exc,
            )
            return None

        return response.json()
