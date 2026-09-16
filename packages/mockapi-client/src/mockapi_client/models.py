"""Modèles Pydantic des ressources exposées par l'API Mock EnerVision.

Ces modèles ne font que constater les données reçues : aucun champ métier
n'a de valeur par défaut (un champ absent doit lever une erreur de
validation, jamais être silencieusement remplacé par 0.0 ou None), et aucun
validateur ne corrige, n'arrondit ou ne borne une valeur — un validateur
peut seulement rejeter. L'imputation/le nettoyage vivent dans
apps/etl_worker/domain/imputation.py (DATA-04), pas ici.
"""

from typing import Literal

from pydantic import BaseModel, Field


class MockApiResource(BaseModel):
    """Base commune : porte le payload JSON d'origine à côté des champs métier.

    `raw_payload` est peuplé par MockApiClient après validation, jamais
    reconstruit depuis les champs Pydantic — et exclu de la sérialisation
    pour ne pas apparaître dans model_dump()/model_dump_json().
    """

    raw_payload: bytes = Field(default=b"", exclude=True, repr=False)


class Site(MockApiResource):
    """Informations statiques d'un site industriel (GET /api/v1/sites)."""

    site_id: str
    site_type: str
    site_name: str
    location: str
    capacity_kw: float
    status: str


class EnergyReading(MockApiResource):
    """Lecture d'un capteur énergétique, à un instant donné.

    Les champs de mesure sont `float | None` sans valeur par défaut : si
    l'API omet un jour l'un de ces champs, la validation doit échouer au
    lieu de laisser passer un 0.0 silencieux.
    """

    timestamp: str
    site_id: str
    site_type: str
    consumption_kw: float | None
    consumption_kwh: float | None
    voltage_v: float | None
    current_a: float | None
    power_factor: float | None
    temperature_celsius: float | None
    humidity_percent: float | None
    null_reasons: list[str]
    data_quality: Literal["good", "partial", "degraded", "critical"]


class Alert(MockApiResource):
    """Alerte de consommation (GET /api/v1/alerts)."""

    alert_id: str
    timestamp: str
    site_id: str
    severity: str
    type: str
    message: str
    value: float | None
    threshold: float
