"""Client HTTP pour l'API Mock EnerVision.

Seul module du projet autorisé à appeler `requests` vers l'API Mock : toute
lecture de données capteurs (sites, relevés, alertes, état des capteurs)
doit passer par ici. Ce module lit ; il ne corrige, ne complète ni ne
filtre rien — cette logique vit dans apps/etl_worker/domain/imputation.py
(DATA-04). Une
erreur d'appel est toujours remontée sous une exception dédiée
(voir exceptions.py), jamais absorbée en valeur par défaut.
"""

import json
import logging
import time
from typing import TypeVar

import requests
from pydantic import BaseModel

from .config import Config
from .exceptions import (
    MockApiConnectionError,
    MockApiHTTPError,
    MockApiNotFoundError,
    MockApiTimeoutError,
    MockApiValidationError,
)
from .models import Alert, EnergyReading, Site

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class MockApiClient:
    """Client de lecture seule pour l'API Mock EnerVision."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        backoff_base: float | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.base_url = base_url or Config.API_BASE_URL
        self.timeout = timeout if timeout is not None else Config.REQUEST_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else Config.MAX_RETRIES
        self.backoff_base = backoff_base if backoff_base is not None else Config.BACKOFF_BASE
        username = username if username is not None else Config.API_USERNAME
        password = password if password is not None else Config.API_PASSWORD
        self.auth = (username, password) if username is not None else None

    def get_sites(self) -> list[Site]:
        """Liste des sites industriels simulés."""
        response = self._request("/api/v1/sites")
        return [self._parse_item(Site, item) for item in response.json()]

    def get_current(self, site_id: str) -> EnergyReading:
        """Mesure instantanée d'un site. Lève MockApiNotFoundError si site_id est inconnu."""
        response = self._request(f"/api/v1/sites/{site_id}/current")
        reading = EnergyReading.model_validate(response.json())
        reading.raw_payload = response.content
        return reading

    def get_readings(
        self,
        site_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        limit: int = 100,
    ) -> list[EnergyReading]:
        """Historique des lectures sur une période (mêmes paramètres que GET /api/v1/readings)."""
        params: dict = {"limit": limit}
        if site_id:
            params["site_id"] = site_id
        if start:
            params["start_time"] = start
        if end:
            params["end_time"] = end
        response = self._request("/api/v1/readings", params=params)
        return [self._parse_item(EnergyReading, item) for item in response.json()]

    def get_alerts(
        self, site_id: str | None = None, severity: str | None = None
    ) -> list[Alert]:
        """Alertes de consommation actives, filtrables par site et/ou sévérité."""
        params = {}
        if site_id:
            params["site_id"] = site_id
        if severity:
            params["severity"] = severity
        response = self._request("/api/v1/alerts", params=params or None)
        return [self._parse_item(Alert, item) for item in response.json()]

    def get_sensors_status(self) -> dict:
        """État de santé des capteurs par site (structure brute de l'API, non typée)."""
        response = self._request("/api/v1/sensors/status")
        return response.json()

    @staticmethod
    def _parse_item(model: type[ModelT], item: dict) -> ModelT:
        parsed = model.model_validate(item)
        # Reconstruit depuis le dict JSON brut (response.json()), jamais depuis
        # le modèle Pydantic, pour que raw_payload reste fidèle à la source.
        parsed.raw_payload = json.dumps(item, ensure_ascii=False).encode("utf-8")
        return parsed

    def _request(self, path: str, params: dict | None = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        attempt = 0
        while True:
            attempt += 1
            try:
                response = requests.get(
                    url, params=params, timeout=self.timeout, auth=self.auth
                )
            except requests.exceptions.Timeout as exc:
                if attempt > self.max_retries:
                    raise MockApiTimeoutError(
                        f"Timeout après {attempt} tentative(s) sur {url}"
                    ) from exc
                logger.warning("Timeout sur %s (tentative %d), retry...", url, attempt)
                self._sleep_backoff(attempt)
                continue
            except requests.exceptions.ConnectionError as exc:
                if attempt > self.max_retries:
                    raise MockApiConnectionError(
                        f"Connexion impossible après {attempt} tentative(s) sur {url}"
                    ) from exc
                logger.warning("Connexion échouée sur %s (tentative %d), retry...", url, attempt)
                self._sleep_backoff(attempt)
                continue

            if response.status_code == 404:
                raise MockApiNotFoundError(self._error_message(response))
            if response.status_code == 422:
                raise MockApiValidationError(self._error_message(response))
            if response.status_code >= 500:
                if attempt > self.max_retries:
                    raise MockApiHTTPError(response.status_code, self._error_message(response))
                logger.warning(
                    "Erreur %d sur %s (tentative %d), retry...",
                    response.status_code,
                    url,
                    attempt,
                )
                self._sleep_backoff(attempt)
                continue

            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as exc:
                raise MockApiHTTPError(response.status_code, self._error_message(response)) from exc

            return response

    def _sleep_backoff(self, attempt: int) -> None:
        time.sleep(self.backoff_base * (2 ** (attempt - 1)))

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        try:
            return str(response.json())
        except ValueError:
            return response.text
