"""Lit le stream Redis alert.detected, alimenté par etl_worker.

XREAD simple, pas de consumer group : le besoin est de diffuser (broadcast)
chaque événement à tous les clients SSE connectés, pas de répartir la charge
entre plusieurs lecteurs. Chaque appelant garde son propre curseur (last_id)
en mémoire locale, aucune persistance côté core_api.
"""

import asyncio
import json
import logging

import redis.asyncio as redis

from application.ports import AlertStreamPort
from domain.entities import AlertEvent

from .config import Config

logger = logging.getLogger(__name__)

STREAM_NAME = "alert.detected"

# Un XREAD qui échoue avant même d'atteindre Redis (connexion refusée) ne
# passe pas par le BLOCK du serveur : sans pause ici, une panne Redis
# transformerait la boucle SSE de chaque client connecté en boucle serrée de
# tentatives de reconnexion.
RECONNECT_DELAY_SECONDS = 1


class RedisAlertStreamReader(AlertStreamPort):
    """Implémentation Redis Streams de AlertStreamPort."""

    def __init__(self, client: "redis.Redis | None" = None, stream_name: str = STREAM_NAME):
        self._client = client or redis.Redis(
            host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
        )
        self._stream_name = stream_name

    async def read_new(self, last_id: str, block_ms: int) -> list[AlertEvent]:
        try:
            response = await self._client.xread(
                {self._stream_name: last_id}, block=block_ms, count=100
            )
        except Exception:  # noqa: BLE001 - Redis en panne : le flux SSE continue, juste vide ce tour
            logger.exception("Lecture du stream %s impossible", self._stream_name)
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
            return []

        if not response:
            return []

        events = []
        for _stream_name, entries in response:
            for entry_id, fields in entries:
                event = self._parse_entry(entry_id, fields)
                if event is not None:
                    events.append(event)
        return events

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _parse_entry(entry_id: str, fields: dict) -> AlertEvent | None:
        try:
            return AlertEvent(
                event_id=entry_id,
                site_id=fields["site_id"],
                timestamp=fields["timestamp"],
                data_quality=fields["data_quality"],
                null_reasons=json.loads(fields.get("null_reasons", "[]")),
            )
        except (KeyError, json.JSONDecodeError):
            logger.warning("Entrée %s du stream %s ignorée (malformée)", entry_id, STREAM_NAME)
            return None
