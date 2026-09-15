"""Écrit le JSON brut horodaté de chaque lecture dans le bucket bronze.

Chemin objet : YYYY/MM/DD/HH/{site_id}_{timestamp}.json. L'horodatage du
chemin et du nom de fichier vient de la lecture elle-même
(EnergyReading.timestamp), pas de l'heure d'ingestion, pour rester
traçable même si le worker prend du retard. Le contenu écrit est
raw_payload (octets bruts de la réponse API), jamais reconstruit depuis
l'objet Pydantic (voir DATA-02 / issue #16).
"""

from datetime import datetime, timezone
from io import BytesIO

from minio import Minio

from .config import Config


class BronzeWriter:
    """Dépose les lectures brutes dans le bucket bronze de MinIO."""

    def __init__(self, client: Minio | None = None, bucket: str | None = None):
        self._client = client or Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=Config.MINIO_SECURE,
        )
        self._bucket = bucket or Config.MINIO_BRONZE_BUCKET

    def write(self, site_id: str, timestamp: str, raw_payload: bytes) -> str:
        """Écrit raw_payload dans le bucket bronze et retourne la clé de l'objet."""
        moment = self._parse_timestamp(timestamp)
        object_key = f"{moment:%Y/%m/%d/%H}/{site_id}_{moment:%Y%m%dT%H%M%S%f}.json"
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
