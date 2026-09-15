"""Client HTTP pour l'API mock EnerVision (voir doc EADL - 04 - API Mock).

Implémente SensorApiPort : c'est le seul module du projet qui connaît
`requests` et l'URL de l'API mock. Il ne lève jamais d'exception, et
convertit les réponses JSON en entités du domaine.
"""

import logging

import requests
from application.ports import SensorApiPort
from domain.entities import Reading, Site

from .config import Config

logger = logging.getLogger(__name__)


class ApiMockClient(SensorApiPort):
    """Appelle l'API mock et ne lève jamais d'exception : les erreurs sont loggées."""

    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = base_url or Config.API_BASE_URL
        self.timeout = timeout if timeout is not None else Config.REQUEST_TIMEOUT

    def get_sites(self) -> list[Site]:
        data = self._get("/api/v1/sites", default=[])
        return [Site.from_dict(item) for item in data]

    def get_current_reading(self, site_id: str) -> Reading | None:
        data = self._get(f"/api/v1/sites/{site_id}/current", default=None)
        return Reading.from_dict(data) if data is not None else None

    def get_readings(
        self,
        site_id: str = None,
        start_time: str = None,
        end_time: str = None,
        limit: int = 100,
    ) -> list[Reading]:
        """Historique des lectures. Mêmes paramètres que GET /api/v1/readings."""
        params = {"limit": limit}
        if site_id:
            params["site_id"] = site_id
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        data = self._get("/api/v1/readings", default=[], params=params)
        return [Reading.from_dict(item) for item in data]

    def _get(self, path: str, default, params: dict = None):
        url = f"{self.base_url}{path}"
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            # API indisponible (timeout, connexion refusée, 4xx/5xx, ...) : pas de crash.
            logger.error("Échec de l'appel à l'API mock (%s) : %s", url, exc)
            return default
        except ValueError as exc:
            logger.error("Réponse JSON invalide depuis l'API mock (%s) : %s", url, exc)
            return default
