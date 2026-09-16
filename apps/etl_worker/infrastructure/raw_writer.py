"""Écrit le JSON brut de chaque lecture dans le bucket raw.

Chemin objet : {site_id}/{YYYY}/{MM}/{DD}/{HH}/{MM_minutes}.json —
partitionné par site d'abord, puis par heure (convention Hive). Adapté à
un usage "historique par site" (creuser un incident sur un site donné) ;
le bucket sert d'archive brute, il n'est pas relu automatiquement par le
worker (l'insertion en base se fait depuis la lecture déjà en mémoire).

Le nom de fichier ne garde que les minutes : plus compact, mais moins
unique que l'horodatage complet — deux écritures du même site dans la
même minute s'écraseraient (peu probable au rythme d'un cycle par
minute, mais possible si le worker redémarre au mauvais moment).

L'arborescence utilise l'heure locale (Europe/Paris, DST géré
automatiquement), fixée explicitement plutôt que de dépendre du fuseau
système : un conteneur Docker est en UTC par défaut, quel que soit le
fuseau de la machine hôte.
"""

from datetime import datetime, timezone
from io import BytesIO
from zoneinfo import ZoneInfo

from minio import Minio

from .config import Config

LOCAL_TZ = ZoneInfo("Europe/Paris")


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
        moment = self._parse_timestamp(timestamp).astimezone(LOCAL_TZ)
        object_key = f"{site_id}/{moment:%Y/%m/%d/%H}/{moment:%M}.json"
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
