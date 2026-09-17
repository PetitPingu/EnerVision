"""Entités métier recommendation : aucune dépendance à HTTP, SQL ou FastAPI."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Site:
    """Un site industriel, tel que nécessaire aux règles de recommandation."""

    site_id: str
    capacity_kw: float


@dataclass(frozen=True)
class Prediction:
    """Une prédiction de consommation pour un site (fournie par le service Prediction)."""

    site_id: str
    predicted_consumption_kw: float
    target_timestamp: str | None = None
    model_version: str | None = None


@dataclass(frozen=True)
class PowerFactorReading:
    """Dernier facteur de puissance mesuré pour un site (table readings_curated)."""

    site_id: str
    power_factor: float


@dataclass(frozen=True)
class Recommendation:
    """Un conseil généré par le moteur de règles pour un site."""

    site_id: str
    type: str
    message: str
    prediction_id: str | None = None
    model_version: str | None = None
    estimated_gain_kwh: float | None = None
