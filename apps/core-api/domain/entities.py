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

    @classmethod
    def from_dict(cls, data: dict) -> "Site":
        return cls(
            site_id=data.get("site_id"),
            site_name=data.get("site_name"),
            site_type=data.get("site_type"),
            location=data.get("location"),
            capacity_kw=data.get("capacity_kw"),
            status=data.get("status"),
        )


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

    @classmethod
    def from_dict(cls, data: dict) -> "Reading":
        return cls(
            site_id=data.get("site_id"),
            timestamp=data.get("timestamp"),
            site_type=data.get("site_type"),
            consumption_kw=data.get("consumption_kw"),
            consumption_kwh=data.get("consumption_kwh"),
            voltage_v=data.get("voltage_v"),
            current_a=data.get("current_a"),
            power_factor=data.get("power_factor"),
            temperature_celsius=data.get("temperature_celsius"),
            humidity_percent=data.get("humidity_percent"),
            null_reasons=data.get("null_reasons") or [],
            data_quality=data.get("data_quality"),
        )
