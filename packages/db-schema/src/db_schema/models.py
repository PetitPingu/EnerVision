"""Modèles ORM (SQLAlchemy) du schéma partagé.

Distincts des dataclasses de domain/entities.py de chaque app : le domaine
applicatif reste pur, ces classes ne sont utilisées que par la couche
infrastructure (accès DB). Tables créées dans le schéma `enervision`
(voir la migration Alembic 0d230748d8a2_bootstrap_extension_and_schema,
qui crée l'extension timescaledb et le schéma avant tout le reste).
"""

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
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


class Recommendation(Base):
    """Conseil généré par le service Recommandation pour un site
    (voir docs/seq_predict_call.md, "Appel au Service Recommandation").

    Pas de clé étrangère vers une table `predictions` : elle n'existe pas
    encore (voir docs/archi_database.md, PREDICTIONS reste "proposé").
    prediction_id reste nullable pour ne pas bloquer sur cette dépendance —
    une recommandation peut de toute façon naître d'un état courant
    critique, sans prédiction.
    """

    __tablename__ = "recommendations"
    __table_args__ = {"schema": "enervision"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[str] = mapped_column(ForeignKey("enervision.sites.site_id"))
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    type: Mapped[str]
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    site: Mapped["Site"] = relationship()
