"""Relit les JSON bruts précédemment déposés dans le bucket bronze par le
worker d'ingestion (voir minio_writer.py), pour le job de transformation
horaire.
"""

from datetime import datetime

from minio import Minio

from .config import Config


class BronzeReader:
    """Liste et lit les objets du bucket bronze pour une heure donnée."""

    def __init__(self, client: Minio | None = None, bucket: str | None = None):
        self._client = client or Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=Config.MINIO_SECURE,
        )
        self._bucket = bucket or Config.MINIO_BRONZE_BUCKET

    def read_hour(self, moment: datetime) -> list[bytes]:
        """Retourne le contenu brut de tous les objets déposés durant l'heure de `moment`."""
        prefix = f"{moment:%Y/%m/%d/%H}/"
        payloads = []
        for obj in self._client.list_objects(self._bucket, prefix=prefix, recursive=True):
            response = self._client.get_object(self._bucket, obj.object_name)
            try:
                payloads.append(response.read())
            finally:
                response.close()
                response.release_conn()
        return payloads
