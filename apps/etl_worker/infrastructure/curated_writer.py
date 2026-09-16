"""Écrit le résultat de la curation (EtlJob) dans readings_curated.

Upsert sur (site_id, timestamp) : une lecture déjà curée (redémarrage,
retraitement) est remplacée, pas dupliquée. Les valeurs finales (brutes
ou imputées) arrivent déjà calculées dans `rows`, produites par
domain.imputation.ConsumptionKwhImputer.
"""

from datetime import datetime, timezone

from db_schema.models import ReadingCurated
from sqlalchemy import create_engine, func
from sqlalchemy.dialects.postgresql import insert

from .config import Config

_TABLE = ReadingCurated.__table__
_KEY_COLUMNS = ("site_id", "timestamp")
_UPDATE_COLUMNS = [c.name for c in _TABLE.columns if c.name not in (*_KEY_COLUMNS, "curated_at")]


class CuratedWriter:
    """Upsert des lectures curées dans Postgres/TimescaleDB."""

    def __init__(self, engine=None):
        self._engine = engine or create_engine(Config.DATABASE_URL)

    def upsert_many(self, rows: list[dict]) -> int:
        """Upsert `rows` (dicts au format des colonnes de readings_curated).
        Retourne le nombre de lignes envoyées à la base."""
        if not rows:
            return 0

        values = [self._to_row_values(row) for row in rows]
        stmt = insert(_TABLE).values(values)
        update_set = {name: getattr(stmt.excluded, name) for name in _UPDATE_COLUMNS}
        update_set["curated_at"] = func.now()
        stmt = stmt.on_conflict_do_update(index_elements=list(_KEY_COLUMNS), set_=update_set)

        with self._engine.begin() as conn:
            conn.execute(stmt)
        return len(values)

    @staticmethod
    def _to_row_values(row: dict) -> dict:
        column_names = {c.name for c in _TABLE.columns}
        values = {key: value for key, value in row.items() if key in column_names}
        values["timestamp"] = CuratedWriter._parse_timestamp(values["timestamp"])
        return values

    @staticmethod
    def _parse_timestamp(timestamp) -> datetime:
        if isinstance(timestamp, datetime):
            moment = timestamp
        else:
            moment = datetime.fromisoformat(timestamp)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment
