"""Client HTTP pour l'API mock EnerVision (voir doc EADL - 04 - API Mock).

Adapte le client partagé `mockapi_client.MockApiClient` — seul module du
monorepo autorisé à appeler `requests` vers l'API mock — au port
SensorApiPort de core_api : ne lève jamais d'exception, les erreurs sont
loggées et une valeur par défaut est retournée à l'appelant.
"""

import logging
import time

from application.ports import SensorApiPort
from domain.entities import Alert, Reading, Site
from mockapi_client import EnergyReading, MockApiClient, MockApiError
from mockapi_client import Alert as MockAlert
from mockapi_client import Site as MockSite

from .config import Config

logger = logging.getLogger(__name__)


class ApiMockClient(SensorApiPort):
    """Appelle l'API mock et ne lève jamais d'exception : les erreurs sont loggées."""

    def __init__(self, base_url: str = None, timeout: float = None):
        self._client = MockApiClient(
            base_url=base_url or Config.API_BASE_URL,
            timeout=timeout if timeout is not None else Config.REQUEST_TIMEOUT,
        )
        self._sites_cache: list[Site] | None = None
        self._sites_cache_at: float = 0.0

    @property
    def base_url(self) -> str:
        return self._client.base_url

    @property
    def timeout(self) -> float:
        return self._client.timeout

    def get_sites(self) -> list[Site]:
        now = time.monotonic()
        if self._sites_cache is not None and now - self._sites_cache_at < Config.SITES_CACHE_TTL:
            return self._sites_cache

        try:
            sites = self._client.get_sites()
        except MockApiError as exc:
            logger.error("Échec de l'appel à l'API mock (get_sites) : %s", exc)
            # En cas d'échec (l'API mock répond parfois 401 sous forte charge,
            # cf. SITES_CACHE_TTL), on préfère resservir le dernier résultat
            # connu plutôt qu'une liste vide qui viderait les sites à l'écran.
            # Le lifespan de l'app préchauffe ce cache au démarrage (cf.
            # presentation/api.py) pour limiter les cas où il est encore vide.
            return self._sites_cache if self._sites_cache is not None else []

        self._sites_cache = [self._to_site(item) for item in sites]
        self._sites_cache_at = now
        return self._sites_cache

    def get_current_reading(self, site_id: str) -> Reading | None:
        try:
            reading = self._client.get_current(site_id)
        except MockApiError as exc:
            logger.error("Échec de l'appel à l'API mock (get_current, %s) : %s", site_id, exc)
            return None
        return self._to_reading(reading)

    def get_readings(
        self,
        site_id: str = None,
        start_time: str = None,
        end_time: str = None,
        limit: int = 100,
    ) -> list[Reading]:
        """Historique des lectures. Mêmes paramètres que GET /api/v1/readings."""
        try:
            readings = self._client.get_readings(
                site_id=site_id, start=start_time, end=end_time, limit=limit
            )
        except MockApiError as exc:
            logger.error("Échec de l'appel à l'API mock (get_readings) : %s", exc)
            return []
        return [self._to_reading(item) for item in readings]

    def get_alerts(self, site_id: str = None, severity: str = None) -> list[Alert]:
        """Alertes de consommation actives, filtrables par site et/ou sévérité."""
        try:
            alerts = self._client.get_alerts(site_id=site_id, severity=severity)
        except MockApiError as exc:
            logger.error("Échec de l'appel à l'API mock (get_alerts) : %s", exc)
            return []
        return [self._to_alert(item) for item in alerts]

    def get_sensors_status(self) -> dict:
        """État de santé des capteurs par site (structure brute de l'API mock)."""
        try:
            return self._client.get_sensors_status()
        except MockApiError as exc:
            logger.error("Échec de l'appel à l'API mock (get_sensors_status) : %s", exc)
            return {}

    @staticmethod
    def _to_site(item: MockSite) -> Site:
        return Site(
            site_id=item.site_id,
            site_name=item.site_name,
            site_type=item.site_type,
            location=item.location,
            capacity_kw=item.capacity_kw,
            status=item.status,
        )

    @staticmethod
    def _to_reading(item: EnergyReading) -> Reading:
        return Reading(
            site_id=item.site_id,
            timestamp=item.timestamp,
            site_type=item.site_type,
            consumption_kw=item.consumption_kw,
            consumption_kwh=item.consumption_kwh,
            voltage_v=item.voltage_v,
            current_a=item.current_a,
            power_factor=item.power_factor,
            temperature_celsius=item.temperature_celsius,
            humidity_percent=item.humidity_percent,
            null_reasons=list(item.null_reasons),
            data_quality=item.data_quality,
        )

    @staticmethod
    def _to_alert(item: MockAlert) -> Alert:
        return Alert(
            alert_id=item.alert_id,
            timestamp=item.timestamp,
            site_id=item.site_id,
            severity=item.severity,
            type=item.type,
            message=item.message,
            value=item.value,
            threshold=item.threshold,
        )
