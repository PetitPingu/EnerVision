"""Modèles ORM (SQLAlchemy) du schéma partagé.

Ces classes servent uniquement à l'accès base de données — le domaine
applicatif de chaque app (domain/entities.py) reste indépendant et n'en
dépend pas.

Toutes les tables vivent dans le schéma `enervision` (créé par la
migration Alembic 0d230748d8a2_bootstrap_extension_and_schema, avant
tout le reste).
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


class ReadingCurated(Base):
    """Lecture prête à consommer comme feature pour un modèle, produite
    par le worker ETL (apps/etl_worker/domain/imputation.py).

    Une seule colonne par champ de mesure — sa valeur finale, pas de
    colonne "brute" séparée. Seul `consumption_kwh` peut être imputé ;
    `imputation_methods` dit ce qui s'est passé pour ce champ sur cette
    ligne :
    - `None` — la valeur était déjà connue.
    - `"forward_fill"` — comblée avec la dernière valeur connue du site.
    - `"no_history"` — manquante, et pas d'historique disponible pour la
      combler (elle reste `None`).
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
