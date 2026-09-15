"""Publie un événement reading.ingested sur Redis Streams pour chaque
lecture nouvellement ingérée — consommé plus tard par le service
d'alerting.
"""

import json

import redis
from mockapi_client import EnergyReading

from .config import Config

STREAM_NAME = "reading.ingested"


class ReadingIngestedPublisher:
    """Publie les lectures ingérées sur le flux Redis reading.ingested."""

    def __init__(self, client: redis.Redis | None = None):
        self._client = client or redis.Redis.from_url(Config.REDIS_URL)

    def publish(self, reading: EnergyReading) -> None:
        self._client.xadd(
            STREAM_NAME,
            {
                "site_id": reading.site_id,
                "timestamp": reading.timestamp,
                "data_quality": reading.data_quality,
                "payload": json.dumps(reading.model_dump(mode="json"), ensure_ascii=False),
            },
        )
