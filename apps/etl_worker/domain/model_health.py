"""Calculs purs pour le monitoring du modèle en production (docs/monitoring_model.md).

Aucun accès I/O ici : uniquement des fonctions qui transforment des lignes
déjà lues (rapprochement + stats de distribution) en métriques. Facilite les
tests unitaires (domain/imputation.py suit la même logique).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import fmean

# En dessous de ce nombre de points sur une fenêtre, la moyenne/écart-type
# est jugée trop instable pour produire un score de drift fiable.
MIN_SAMPLE_SIZE = 30

# Tolérance du rapprochement prédiction <-> mesure réelle : readings_curated.timestamp
# porte la précision de l'horodatage brut renvoyé par l'API mock (secondes/microsecondes),
# jamais aligné pile sur la minute demandée à /predict. Sans tolérance, un rapprochement
# par égalité stricte ne matcherait quasiment jamais en usage réel (constaté en testant
# en conditions réelles). 300s = 5x l'intervalle de poll par défaut de l'ETL (60s),
# marge confortable pour un cycle manqué.
RECONCILIATION_TOLERANCE_SECONDS = 300

# Tranches d'horizon = target_timestamp - generated_at (délai entre l'appel
# /predict et l'instant prédit). Sert à faire grandir la marge d'erreur
# affichée sur le dashboard avec l'horizon (docs/monitoring_model.md) : une
# prédiction à 7 jours n'a pas la même fiabilité qu'une prédiction à 10 min.
# Bornes en secondes, [min, max).
HORIZON_BUCKETS: list[tuple[str, float, float]] = [
    ("0-1h", 0, 3600),
    ("1-3h", 3600, 3 * 3600),
    ("3-6h", 3 * 3600, 6 * 3600),
    ("6-12h", 6 * 3600, 12 * 3600),
    ("12-24h", 12 * 3600, 24 * 3600),
    ("1-3j", 24 * 3600, 3 * 24 * 3600),
    ("3-7j", 3 * 24 * 3600, 7 * 24 * 3600),
]

# Contrairement à MIN_SAMPLE_SIZE (drift, alarme temps réel), un seuil plus
# bas suffit ici : ce profil d'erreur par horizon est un diagnostic de fond
# qui évolue lentement, pas un signal d'alerte — un peu de bruit sur une
# tranche est acceptable, l'absence totale de valeur (bande qui disparaît)
# serait pire pour l'expérience utilisateur qu'une estimation approximative.
MIN_HORIZON_SAMPLE_SIZE = 5


@dataclass(frozen=True)
class RawPrediction:
    """Une prédiction telle que loguée par apps/prediction, avant rapprochement."""

    site_id: str
    target_timestamp: datetime
    predicted_consumption_kwh: float
    model_version: str | None
    generated_at: datetime


@dataclass(frozen=True)
class ActualReading:
    """Une mesure réelle candidate au rapprochement (readings_curated)."""

    site_id: str
    timestamp: datetime
    consumption_kwh: float


@dataclass(frozen=True)
class ReconciledPrediction:
    """Une prédiction pour laquelle la mesure réelle est désormais connue."""

    site_id: str
    target_timestamp: datetime
    predicted_consumption_kwh: float
    actual_consumption_kwh: float
    model_version: str | None
    generated_at: datetime


def reconcile_predictions(
    predictions: list[RawPrediction],
    readings: list[ActualReading],
    tolerance_seconds: int = RECONCILIATION_TOLERANCE_SECONDS,
) -> list[ReconciledPrediction]:
    """Associe chaque prédiction à la mesure réelle la plus proche dans le
    temps pour le même site, dans la limite de `tolerance_seconds`.

    Une prédiction sans mesure suffisamment proche reste orpheline (voir
    docs/monitoring_model.md, "Cas non rapprochables") : elle n'apparaît
    simplement pas dans le résultat, plutôt que d'être associée à une
    mesure trop éloignée dans le temps pour être pertinente."""
    readings_by_site: dict[str, list[ActualReading]] = defaultdict(list)
    for reading in readings:
        readings_by_site[reading.site_id].append(reading)

    reconciled = []
    for prediction in predictions:
        best_reading = None
        best_diff_seconds = None
        for reading in readings_by_site.get(prediction.site_id, []):
            diff_seconds = abs((reading.timestamp - prediction.target_timestamp).total_seconds())
            if diff_seconds <= tolerance_seconds and (
                best_diff_seconds is None or diff_seconds < best_diff_seconds
            ):
                best_reading = reading
                best_diff_seconds = diff_seconds

        if best_reading is not None:
            reconciled.append(
                ReconciledPrediction(
                    site_id=prediction.site_id,
                    target_timestamp=prediction.target_timestamp,
                    predicted_consumption_kwh=prediction.predicted_consumption_kwh,
                    actual_consumption_kwh=best_reading.consumption_kwh,
                    model_version=prediction.model_version,
                    generated_at=prediction.generated_at,
                )
            )

    return reconciled


@dataclass(frozen=True)
class DistributionStats:
    """Moyenne/écart-type/effectif de consumption_kwh sur une fenêtre donnée."""

    mean: float
    stddev: float
    count: int


def compute_mae_over_window(
    reconciled: list[ReconciledPrediction],
    now: datetime,
    window: timedelta,
) -> dict[str, float]:
    """MAE glissante par site, sur les prédictions rapprochées dont
    target_timestamp tombe dans les `window` dernières (par rapport à `now`).

    Généralise compute_mae_24h : sert aussi bien à la carte "24h" du
    dashboard qu'à la carte "7 jours" (docs/monitoring_model.md), sans
    dupliquer la logique de filtrage/moyenne.
    """
    window_start = now - window
    errors_by_site: dict[str, list[float]] = defaultdict(list)

    for row in reconciled:
        if window_start <= row.target_timestamp <= now:
            error = abs(row.predicted_consumption_kwh - row.actual_consumption_kwh)
            errors_by_site[row.site_id].append(error)

    return {site: fmean(errors) for site, errors in errors_by_site.items() if errors}


def compute_mae_24h(
    reconciled: list[ReconciledPrediction],
    now: datetime,
) -> dict[str, float]:
    """MAE glissante 24h par site — voir compute_mae_over_window."""
    return compute_mae_over_window(reconciled, now, timedelta(hours=24))


def compute_mae_7d(
    reconciled: list[ReconciledPrediction],
    now: datetime,
) -> dict[str, float]:
    """MAE glissante 7 jours par site — voir compute_mae_over_window."""
    return compute_mae_over_window(reconciled, now, timedelta(days=7))


def latest_model_version_by_site(
    reconciled: list[ReconciledPrediction],
    now: datetime,
) -> dict[str, str]:
    """Version de modèle la plus récente vue par site, sur les prédictions
    rapprochées des 24 dernières heures (même fenêtre que compute_mae_24h)."""
    window_start = now - timedelta(hours=24)
    latest: dict[str, tuple[datetime, str]] = {}

    for row in reconciled:
        if row.model_version is None or not (window_start <= row.target_timestamp <= now):
            continue
        current = latest.get(row.site_id)
        if current is None or row.target_timestamp > current[0]:
            latest[row.site_id] = (row.target_timestamp, row.model_version)

    return {site: version for site, (_, version) in latest.items()}


def compute_drift_score(recent: DistributionStats, training: DistributionStats) -> float | None:
    """Compare la distribution récente de consumption_kwh à celle de la
    fenêtre d'entraînement (écart de moyenne/écart-type normalisé).

    Retourne None si l'un des deux échantillons est trop petit pour être
    fiable, ou si training.stddev est nul (site quasi constant à
    l'entraînement : tout écart serait mécaniquement énorme).
    """
    if recent.count < MIN_SAMPLE_SIZE or training.count < MIN_SAMPLE_SIZE:
        return None
    if training.stddev == 0:
        return None

    z_mean = (recent.mean - training.mean) / training.stddev
    z_std = recent.stddev / training.stddev

    return max(abs(z_mean), abs(z_std - 1))


def horizon_bucket_label(horizon_seconds: float) -> str | None:
    """Tranche d'horizon correspondant à `horizon_seconds`, ou None si hors
    bornes (négatif, ou au-delà de la plus grande tranche définie)."""
    if horizon_seconds < 0:
        return None
    for label, lower, upper in HORIZON_BUCKETS:
        if lower <= horizon_seconds < upper:
            return label
    return None


def compute_mae_by_horizon(
    reconciled: list[ReconciledPrediction],
) -> dict[str, dict[str, float]]:
    """MAE par tranche d'horizon (target_timestamp - generated_at), par site.

    Contrairement à compute_mae_24h (glissante sur target_timestamp, pour le
    suivi temps réel), celle-ci regarde tout l'historique rapproché fourni
    (généralement plusieurs jours/semaines) : le but est de caractériser
    comment l'erreur du modèle croît avec l'horizon de prévision (utilisé
    pour dessiner une marge d'erreur qui s'élargit dans le dashboard), pas
    de suivre une dérive récente.

    Une tranche avec moins de MIN_HORIZON_SAMPLE_SIZE points est omise du
    résultat (échantillon jugé trop instable).
    """
    errors_by_site_bucket: dict[tuple[str, str], list[float]] = defaultdict(list)

    for row in reconciled:
        horizon_seconds = (row.target_timestamp - row.generated_at).total_seconds()
        bucket = horizon_bucket_label(horizon_seconds)
        if bucket is None:
            continue
        error = abs(row.predicted_consumption_kwh - row.actual_consumption_kwh)
        errors_by_site_bucket[(row.site_id, bucket)].append(error)

    result: dict[str, dict[str, float]] = defaultdict(dict)
    for (site_id, bucket), errors in errors_by_site_bucket.items():
        if len(errors) >= MIN_HORIZON_SAMPLE_SIZE:
            result[site_id][bucket] = fmean(errors)

    return dict(result)
