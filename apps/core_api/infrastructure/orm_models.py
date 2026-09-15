"""Modèles ORM (SQLAlchemy) mappés aux entités du domaine.

Distincts des dataclasses de domain/entities.py : le domaine reste pur, ces
classes ne sont utilisées que par la couche infrastructure (accès DB).
Tables créées dans le schéma `enervision` (voir db/init/001-init-timescaledb.sql).
"""

from datetime import datetime

from sqlalchemy import ARRAY, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Site(Base):
    """Un site industriel suivi par EnerVision."""

    __tablename__ = "sites"
    __table_args__ = {"schema": "enervision"}

    site_id: Mapped[str] = mapped_column(String, primary_key=True)
    site_name: Mapped[str | None]
    site_type: Mapped[str | None]
    location: Mapped[str | None]
    capacity_kw: Mapped[float | None]
    status: Mapped[str | None]

    readings: Mapped[list["Reading"]] = relationship(back_populates="site")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="site")


class Reading(Base):
    """Une mesure de capteurs pour un site, à un instant donné.

    Clé primaire composite (site_id, timestamp) : `timestamp` est la colonne de
    partitionnement attendue par TimescaleDB pour transformer cette table en
    hypertable (voir la migration Alembic correspondante).
    """

    __tablename__ = "readings"
    __table_args__ = {"schema": "enervision"}

    site_id: Mapped[str] = mapped_column(ForeignKey("enervision.sites.site_id"), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(primary_key=True)
    site_type: Mapped[str | None]
    consumption_kw: Mapped[float | None]
    consumption_kwh: Mapped[float | None]
    voltage_v: Mapped[float | None]
    current_a: Mapped[float | None]
    power_factor: Mapped[float | None]
    temperature_celsius: Mapped[float | None]
    humidity_percent: Mapped[float | None]
    null_reasons: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    data_quality: Mapped[str | None]

    site: Mapped["Site"] = relationship(back_populates="readings")


class Alert(Base):
    """Une alerte de consommation sur un site."""

    __tablename__ = "alerts"
    __table_args__ = {"schema": "enervision"}

    alert_id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime]
    site_id: Mapped[str] = mapped_column(ForeignKey("enervision.sites.site_id"))
    severity: Mapped[str | None]
    type: Mapped[str | None]
    message: Mapped[str | None]
    value: Mapped[float | None]
    threshold: Mapped[float | None]

    site: Mapped["Site"] = relationship(back_populates="alerts")


class ConsumptionReading(Base):
    """Lecture transformée depuis le bucket MinIO raw par le Worker ETL
    (issue #19, voir docs/seq_etl.md).

    Pas de clé étrangère vers Site : le job de transformation ne
    synchronise pas la table sites, site_id est un simple champ texte.
    """

    __tablename__ = "consumption_readings"
    __table_args__ = {"schema": "enervision"}

    site_id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(primary_key=True)
    site_type: Mapped[str | None]
    consumption_kw: Mapped[float | None]
    consumption_kwh: Mapped[float | None]
    voltage_v: Mapped[float | None]
    current_a: Mapped[float | None]
    power_factor: Mapped[float | None]
    temperature_celsius: Mapped[float | None]
    humidity_percent: Mapped[float | None]
    null_reasons: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    data_quality: Mapped[str | None]
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now())
