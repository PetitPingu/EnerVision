"""Entités métier EnerVision : aucune dépendance à HTTP, SQL ou FastAPI."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Site:
    """Un site industriel suivi par EnerVision."""

    site_id: str
    site_name: str | None = None
    site_type: str | None = None
    location: str | None = None
    capacity_kw: float | None = None
    status: str | None = None


@dataclass(frozen=True)
class Reading:
    """Une mesure de capteurs pour un site, à un instant donné."""

    site_id: str
    timestamp: str
    site_type: str | None = None
    consumption_kw: float | None = None
    consumption_kwh: float | None = None
    voltage_v: float | None = None
    current_a: float | None = None
    power_factor: float | None = None
    temperature_celsius: float | None = None
    humidity_percent: float | None = None
    null_reasons: list = field(default_factory=list)
    data_quality: str | None = None


@dataclass(frozen=True)
class Alert:
    """Une alerte de consommation sur un site."""

    alert_id: str
    timestamp: str
    site_id: str
    severity: str | None = None
    type: str | None = None
    message: str | None = None
    value: float | None = None
    threshold: float | None = None


@dataclass(frozen=True)
class AlertEvent:
    """Une transition data_quality publiée par etl_worker sur Redis Streams."""

    event_id: str
    site_id: str
    timestamp: str
    data_quality: str
    null_reasons: list = field(default_factory=list)

    @property
    def kind(self) -> str:
        """"recovery" (good), "minor_alert" (partial : souci mineur identifié
        mais réel), sinon "alert" (degraded/critical)."""
        if self.data_quality == "good":
            return "recovery"
        if self.data_quality == "partial":
            return "minor_alert"
        return "alert"
