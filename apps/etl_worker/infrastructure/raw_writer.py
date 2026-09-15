"""Écrit le JSON brut de chaque lecture dans le bucket raw.

Chemin objet : {date}/{site_id}_{timestamp}.json — un fichier par lecture
(l'horodatage de la lecture rend la clé unique), pour ne perdre aucune
donnée intraday : contrairement à une clé {date}/{site_id}.json, chaque
nouvelle lecture du jour vient s'ajouter plutôt que d'écraser la
précédente.
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
        object_key = f"{moment:%Y-%m-%d}/{site_id}_{moment:%Y%m%dT%H%M%S%f}.json"
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
