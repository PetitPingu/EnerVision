"""Lit les données nécessaires au job de monitoring du modèle (predictions_log
rapprochées avec readings_curated, stats de distribution de consumption_kwh).

Même stack que CuratedWriter/PostgresTrainingDataReader : SQLAlchemy sync,
moteur créé une fois, requêtes directes sans ORM lourd (agrégats calculés
côté Postgres, pas en Python).
"""

from datetime import datetime, timedelta, timezone

from db_schema.models import PredictionLog, ReadingCurated
from sqlalchemy import create_engine, func, select

from domain.model_health import (
    RECONCILIATION_TOLERANCE_SECONDS,
    ActualReading,
    DistributionStats,
    ReconciledPrediction,
    RawPrediction,
    reconcile_predictions,
)

from .config import Config

# Format produit par apps/prediction/infrastructure/model_store/minio_store.py
# (utc_version_timestamp) : pas de ':' dans la clé, safe pour MinIO/S3.
_MODEL_VERSION_FORMAT = "%Y-%m-%dT%H-%M-%SZ"


class ModelHealthReader:
    """Accès Postgres pour le job de rapprochement + drift."""

    def __init__(self, engine=None):
        self._engine = engine or create_engine(Config.DATABASE_URL)

    def fetch_reconciled_predictions(self, since: datetime) -> list[ReconciledPrediction]:
        """Prédictions dont target_timestamp >= `since`, rapprochées de la
        mesure réelle la plus proche dans readings_curated (même site),
        dans la limite de RECONCILIATION_TOLERANCE_SECONDS — pas d'égalité
        stricte sur le timestamp : readings_curated.timestamp porte la
        précision brute de l'API mock, jamais alignée pile sur la minute
        demandée à /predict (voir domain/model_health.py)."""
        tolerance = timedelta(seconds=RECONCILIATION_TOLERANCE_SECONDS)
        predictions = self._fetch_raw_predictions(since)
        if not predictions:
            return []

        site_ids = sorted({p.site_id for p in predictions})
        earliest_target = min(p.target_timestamp for p in predictions)
        latest_target = max(p.target_timestamp for p in predictions)
        readings = self._fetch_actual_readings(
            site_ids,
            start=earliest_target - tolerance,
            end=latest_target + tolerance,
        )

        return reconcile_predictions(predictions, readings)

    def _fetch_raw_predictions(self, since: datetime) -> list[RawPrediction]:
        stmt = select(
            PredictionLog.site_id,
            PredictionLog.target_timestamp,
            PredictionLog.predicted_consumption_kwh,
            PredictionLog.model_version,
            PredictionLog.generated_at,
        ).where(PredictionLog.target_timestamp >= since)

        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()

        return [
            RawPrediction(
                site_id=row.site_id,
                target_timestamp=row.target_timestamp,
                predicted_consumption_kwh=row.predicted_consumption_kwh,
                model_version=row.model_version,
                generated_at=row.generated_at,
            )
            for row in rows
        ]

    def _fetch_actual_readings(
        self, site_ids: list[str], start: datetime, end: datetime
    ) -> list[ActualReading]:
        stmt = select(
            ReadingCurated.site_id,
            ReadingCurated.timestamp,
            ReadingCurated.consumption_kwh,
        ).where(
            ReadingCurated.site_id.in_(site_ids),
            ReadingCurated.consumption_kwh.is_not(None),
            ReadingCurated.timestamp >= start,
            ReadingCurated.timestamp <= end,
        )

        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()

        return [
            ActualReading(
                site_id=row.site_id,
                timestamp=row.timestamp,
                consumption_kwh=row.consumption_kwh,
            )
            for row in rows
        ]

    def fetch_consumption_stats(
        self, site_id: str, start: datetime, end: datetime
    ) -> DistributionStats:
        """Moyenne/écart-type/effectif de consumption_kwh pour un site sur
        [start, end)."""
        stmt = select(
            func.avg(ReadingCurated.consumption_kwh),
            func.stddev_samp(ReadingCurated.consumption_kwh),
            func.count(ReadingCurated.consumption_kwh),
        ).where(
            ReadingCurated.site_id == site_id,
            ReadingCurated.consumption_kwh.is_not(None),
            ReadingCurated.timestamp >= start,
            ReadingCurated.timestamp < end,
        )

        with self._engine.connect() as conn:
            mean, stddev, count = conn.execute(stmt).one()

        return DistributionStats(mean=mean or 0.0, stddev=stddev or 0.0, count=count or 0)


def parse_model_version(model_version: str) -> datetime | None:
    """Reconstruit la date d'entraînement à partir de `model_version`
    (= metadata.trained_at, cf. apps/prediction). None si le format est
    inattendu plutôt que de faire planter le job de monitoring."""
    try:
        return datetime.strptime(model_version, _MODEL_VERSION_FORMAT).replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None
