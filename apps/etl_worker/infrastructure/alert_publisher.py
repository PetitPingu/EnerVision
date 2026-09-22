"""Publie les transitions de data_quality sur le stream Redis alert.detected.

Le stream est trimmé (`MAXLEN ~ 500`) : il sert de tampon temps réel pour un
dashboard qui se connecte/reconnecte, pas d'historique/audit durable.
"""

import json

import redis

from .config import Config

STREAM_NAME = "alert.detected"
STREAM_MAXLEN = 500


class AlertPublisher:
    """Envoie un événement de transition data_quality sur Redis Streams."""

    def __init__(self, client: "redis.Redis | None" = None):
        self._client = client or redis.Redis(
            host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
        )

    def publish(
        self, site_id: str, timestamp: str, data_quality: str, null_reasons: list[str]
    ) -> None:
        """XADD sur alert.detected. Laisse remonter toute erreur Redis :
        c'est à l'appelant (EtlJob) de décider de logger et continuer."""
        fields = {
            "site_id": site_id,
            "timestamp": timestamp,
            "data_quality": data_quality,
            "null_reasons": json.dumps(null_reasons),
        }
        self._client.xadd(STREAM_NAME, fields, maxlen=STREAM_MAXLEN, approximate=True)
