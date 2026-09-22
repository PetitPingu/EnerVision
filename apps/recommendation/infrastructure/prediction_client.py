"""Client HTTP vers le service Prediction (voir docs/seq_predict_call.md,
"Appel au Service Recommandation") : GET {PREDICTION_URL}/predict?site_id=...

Ne lève jamais d'exception : les erreurs (y compris service indisponible,
tant qu'il n'est pas encore déployé) sont loggées et None est retourné —
même convention que ApiMockClient dans core_api.
"""

import logging
from datetime import UTC, datetime

import requests
from application.ports import PredictionApiPort
from domain.entities import Prediction

from .config import Config

logger = logging.getLogger(__name__)


class PredictionHttpClient(PredictionApiPort):
    """Appelle le service Prediction pour la prédiction de consommation d'un site."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self._base_url = (base_url or Config.PREDICTION_URL).rstrip("/")
        self._timeout = timeout if timeout is not None else Config.REQUEST_TIMEOUT

    def get_prediction(self, site_id: str) -> Prediction | None:
        try:
            response = requests.get(
                f"{self._base_url}/predict",
                params={"site_id": site_id, "timestamp": datetime.now(UTC).isoformat()},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            return Prediction(
                site_id=data["site_id"],
                predicted_consumption_kw=data["predicted_consumption_kwh"],
                target_timestamp=data.get("target_timestamp"),
                model_version=data.get("model_version"),
            )
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            logger.error("Échec de l'appel au service Prediction (site_id=%s) : %s", site_id, exc)
            return None
