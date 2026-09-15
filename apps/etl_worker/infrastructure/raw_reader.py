"""Relit les JSON bruts déposés dans le bucket raw pour le job de
transformation (docs/seq_etl.md).
"""

from datetime import date

from minio import Minio

from .config import Config


class RawReader:
    """Liste et lit les objets du bucket raw pour une date donnée."""

    def __init__(self, client: Minio | None = None, bucket: str | None = None):
        self._client = client or Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=Config.MINIO_SECURE,
        )
        self._bucket = bucket or Config.MINIO_RAW_BUCKET

    def read_date(self, day: date) -> list[bytes]:
        """Retourne le contenu brut de tous les objets déposés pour cette date."""
        prefix = f"{day:%Y-%m-%d}/"
        payloads = []
        for obj in self._client.list_objects(self._bucket, prefix=prefix, recursive=True):
            response = self._client.get_object(self._bucket, obj.object_name)
            try:
                payloads.append(response.read())
            finally:
                response.close()
                response.release_conn()
        return payloads
