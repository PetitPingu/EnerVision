"""Modèles ORM (SQLAlchemy) du schéma partagé.

Distincts des dataclasses de domain/entities.py de chaque app : le domaine
applicatif reste pur, ces classes ne sont utilisées que par la couche
infrastructure (accès DB). Tables créées dans le schéma `enervision`
(voir la migration Alembic 0d230748d8a2_bootstrap_extension_and_schema,
qui crée l'extension timescaledb et le schéma avant tout le reste).
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

    alerts: Mapped[list["Alert"]] = relationship(back_populates="site")


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


class ReadingCurated(Base):
    """Lecture transformée (raw -> curated) par le job de transformation
    (apps/etl_worker/domain/imputation.py), prête à consommer comme
    feature pour l'entraînement de modèle.

    Une seule colonne par champ de mesure : sa valeur finale (la valeur
    brute si connue, sinon une valeur imputée, sinon None). Pas de
    duplication brut/imputé — `imputation_methods` (nullable) indique le
    sort de `consumption_kwh` (le seul champ imputé) pour cette lecture :
    None si la valeur était déjà connue, "forward_fill" si elle a été
    comblée par la dernière valeur connue, "no_history" si elle est
    restée None faute d'historique disponible (distinct d'un trou
    normal comblé).
    """

    __tablename__ = "readings_curated"
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

    imputation_methods: Mapped[str | None] = mapped_column(String, default=None)
    null_reasons: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    data_quality: Mapped[str | None]
    curated_at: Mapped[datetime] = mapped_column(server_default=func.now())
