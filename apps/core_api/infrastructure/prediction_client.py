"""Client HTTP pour le service prediction (voir apps/prediction).

Relaie les prévisions de consommation vers le service interne `prediction`
(adressé via PREDICTION_URL). Ne lève jamais d'exception : les erreurs sont
loggées et `None` est retourné à l'appelant, qui traduit ça en 502.
"""

import logging

import requests

from .config import Config

logger = logging.getLogger(__name__)


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
