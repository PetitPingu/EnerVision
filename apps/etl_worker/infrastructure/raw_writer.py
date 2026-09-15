"""Écrit le JSON brut de chaque lecture dans le bucket raw.

Chemin objet : {YYYY}/{MM}/{DD}/{HH}/{numéro_site}_{MM_minutes}.json —
partitionnement par heure (convention Hive, courante pour un data lake :
liste/filtre efficace par période). Le nom de fichier ne garde que le
numéro du site et les minutes : plus compact, mais moins unique que
l'horodatage complet — deux écritures du même site dans la même minute
s'écraseraient (peu probable au rythme d'un cycle par minute, mais
possible si le worker redémarre au mauvais moment).

L'arborescence utilise l'heure locale (Europe/Paris, DST géré
automatiquement), fixée explicitement plutôt que de dépendre du fuseau
système : un conteneur Docker est en UTC par défaut, quel que soit le
fuseau de la machine hôte.
"""

import re
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
        site_number = self._site_number(site_id)
        object_key = f"{moment:%Y/%m/%d/%H}/{site_number}_{moment:%M}.json"
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

    @staticmethod
    def _site_number(site_id: str) -> str:
        """Extrait le numéro du site (ex: "SITE001" -> "001")."""
        match = re.search(r"\d+", site_id)
        return match.group() if match else site_id
