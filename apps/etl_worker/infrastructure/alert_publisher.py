"""Publie une alerte sur Redis Streams pour toute lecture critical/hors
seuil, détectée dès l'ingestion (cycle de 60s) plutôt qu'au prochain
passage du job de transformation.
"""

import redis
from mockapi_client import EnergyReading

from .config import Config

STREAM_NAME = "alert.detected"


class AlertPublisher:
    """Publie les lectures critiques sur le flux Redis alert.detected."""

    def __init__(self, client: redis.Redis | None = None):
        self._client = client or redis.Redis.from_url(Config.REDIS_URL)

    def publish(self, reading: EnergyReading) -> None:
        self._client.xadd(
            STREAM_NAME,
            {
                "site_id": reading.site_id,
                "timestamp": reading.timestamp,
                "data_quality": reading.data_quality,
            },
        )
