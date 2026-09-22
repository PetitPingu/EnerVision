"""Job de rapprochement + drift (docs/monitoring_model.md).

Tourne à intervalle plus large que EtlJob (pas besoin d'une fraîcheur à la
minute pour une métrique glissante 24h) : rapproche les prédictions
loguées par apps/prediction avec la mesure réelle arrivée entre-temps dans
readings_curated, calcule la MAE glissante par site, puis compare la
distribution récente de consumption_kwh à celle de la fenêtre
d'entraînement du modèle actif pour détecter un drift.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from domain.model_health import (
    compute_drift_score,
    compute_mae_24h,
    compute_mae_7d,
    compute_mae_by_horizon,
    latest_model_version_by_site,
)
from infrastructure.config import Config
from infrastructure.model_health_metrics import publish_model_health
from infrastructure.model_health_reader import ModelHealthReader, parse_model_version

logger = logging.getLogger(__name__)


class ModelHealthJob:
    """Calcule MAE glissante 24h + drift par site, et alimente Prometheus."""

    def __init__(
        self,
        reader: ModelHealthReader | None = None,
        training_window_days: int = Config.TRAINING_WINDOW_DAYS,
        horizon_profile_lookback_days: int = Config.HORIZON_PROFILE_LOOKBACK_DAYS,
    ):
        self.reader = reader or ModelHealthReader()
        self.training_window_days = training_window_days
        self.horizon_profile_lookback_days = horizon_profile_lookback_days

    def run(self) -> None:
        now = datetime.now(timezone.utc)
        # Fenêtre large (pas seulement 24h) : compute_mae_24h et
        # latest_model_version_by_site se re-filtrent déjà en interne sur les
        # 24 dernières heures, donc élargir ici sert uniquement à alimenter
        # compute_mae_by_horizon avec assez d'historique pour les tranches
        # d'horizon longues (jusqu'à 7j, voir domain/model_health.py) — une
        # seule requête de rapprochement pour les deux usages.
        lookback_start = now - timedelta(days=self.horizon_profile_lookback_days)

        try:
            reconciled = self.reader.fetch_reconciled_predictions(since=lookback_start)
        except Exception as exc:  # noqa: BLE001 - Postgres en panne : on réessaiera au prochain cycle
            self._log(status="reconciliation_read_error", error=str(exc))
            return

        mae_by_site = compute_mae_24h(reconciled, now)
        mae_7d_by_site = compute_mae_7d(reconciled, now)
        model_version_by_site = latest_model_version_by_site(reconciled, now)
        drift_by_site = self._compute_drift_by_site(model_version_by_site, now)
        mae_by_horizon_by_site = compute_mae_by_horizon(reconciled)

        try:
            publish_model_health(
                mae_by_site,
                drift_by_site,
                model_version_by_site,
                mae_by_horizon_by_site,
                mae_7d_by_site,
            )
        except Exception as exc:  # noqa: BLE001 - ne doit jamais faire tomber le job
            self._log(status="metrics_publish_error", error=str(exc))
            return

        self._log(
            status="published",
            sites_reconciled=len(mae_by_site),
            sites_with_drift_score=len(drift_by_site),
            sites_with_horizon_profile=len(mae_by_horizon_by_site),
        )

    def _compute_drift_by_site(
        self, model_version_by_site: dict[str, str], now: datetime
    ) -> dict[str, float]:
        drift_by_site: dict[str, float] = {}
        recent_start = now - timedelta(hours=24)

        for site_id, model_version in model_version_by_site.items():
            trained_at = parse_model_version(model_version)
            if trained_at is None:
                continue

            training_start = trained_at - timedelta(days=self.training_window_days)

            try:
                training_stats = self.reader.fetch_consumption_stats(
                    site_id, training_start, trained_at
                )
                recent_stats = self.reader.fetch_consumption_stats(site_id, recent_start, now)
            except Exception as exc:  # noqa: BLE001 - un site en erreur ne doit pas bloquer les autres
                self._log(status="drift_read_error", site=site_id, error=str(exc))
                continue

            score = compute_drift_score(recent_stats, training_stats)
            if score is not None:
                drift_by_site[site_id] = score

        return drift_by_site

    @staticmethod
    def _log(status: str, **extra) -> None:
        logger.info(json.dumps({"status": status, **extra}))
