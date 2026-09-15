"""Écrit le JSON brut de chaque lecture dans le bucket raw.

Chemin objet : {date}/{site_id}.json — conforme au diagramme d'ingestion
(docs/seq_etl.md) : un fichier par site et par jour, écrasé à chaque
nouvelle lecture du jour.
"""

from datetime import datetime, timezone
from io import BytesIO

from minio import Minio

from .config import Config


class RawWriter:
    """Dépose les lectures brutes dans le bucket raw de MinIO."""

    def __init__(self, client: Minio | None = None, bucket: str | None = None):
        self._client = client or Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=Config.MINIO_SECURE,
        )
        self._bucket = bucket or Config.MINIO_RAW_BUCKET

    def write(self, site_id: str, timestamp: str, raw_payload: bytes) -> str:
        """Écrit raw_payload dans le bucket raw et retourne la clé de l'objet."""
        moment = self._parse_timestamp(timestamp)
        object_key = f"{moment:%Y-%m-%d}/{site_id}.json"
        self._client.put_object(
            self._bucket,
            object_key,
            data=BytesIO(raw_payload),
            length=len(raw_payload),
            content_type="application/json",
        )
        return object_key

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime:
        moment = datetime.fromisoformat(timestamp)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment
