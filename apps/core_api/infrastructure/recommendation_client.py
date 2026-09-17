"""Client HTTP pour le service recommendation (voir apps/recommendation).

Relaie les recommandations vers le service interne `recommendation` (adressé
via RECOMMENDATION_URL). Ne lève jamais d'exception : les erreurs sont
loggées et `None` est retourné à l'appelant, qui traduit ça en 502.
"""

import logging

import requests

from .config import Config

logger = logging.getLogger(__name__)


class RecommendationApiClient:
    """Appelle le service recommendation et ne lève jamais d'exception."""

    def __init__(self, base_url: str = None, timeout: float = None):
        self._base_url = (base_url or Config.RECOMMENDATION_URL).rstrip("/")
        self._timeout = timeout if timeout is not None else Config.REQUEST_TIMEOUT

    def get_recommendations(self, site_id: str) -> list | None:
        """Relaie GET /api/v1/recommendations du service recommendation."""
        try:
            response = requests.get(
                f"{self._base_url}/api/v1/recommendations",
                params={"site_id": site_id},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error(
                "Échec de l'appel au service recommendation (site_id=%s) : %s",
                site_id,
                exc,
            )
            return None

        return response.json()
