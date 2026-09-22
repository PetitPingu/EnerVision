"""Lit les lectures JSON du bucket raw MinIO.

Complément de RawWriter : parcourt les objets déjà écrits dans le datalake
pour un retraitement vers readings_curated (voir backfill_curated_from_raw).
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from minio import Minio
from mockapi_client import EnergyReading

from .config import Config


@dataclass(frozen=True)
class RawObject:
    """Objet MinIO parsé en lecture métier."""

    object_key: str
    reading: EnergyReading


class RawReader:
    """Liste et lit les fichiers JSON du bucket raw."""

    def __init__(self, client: Minio | None = None, bucket: str | None = None):
        self._client = client or Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=Config.MINIO_SECURE,
        )
        self._bucket = bucket or Config.MINIO_RAW_BUCKET

    def list_object_keys(self, prefix: str = "") -> list[str]:
        """Retourne les clés .json triées (ordre chronologique par site)."""
        keys: list[str] = []
        for obj in self._client.list_objects(self._bucket, prefix=prefix, recursive=True):
            if obj.object_name.endswith(".json"):
                keys.append(obj.object_name)
        return sorted(keys)

    def read_object(self, object_key: str) -> EnergyReading:
        """Charge et valide un JSON brut en EnergyReading."""
        response = self._client.get_object(self._bucket, object_key)
        try:
            payload = response.read()
        finally:
            response.close()
            response.release_conn()

        reading = EnergyReading.model_validate_json(payload)
        reading.raw_payload = payload
        return reading

    @staticmethod
    def parse_timestamp(timestamp: str) -> datetime:
        moment = datetime.fromisoformat(timestamp)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment
