"""Ports (interfaces) que l'infrastructure doit implémenter.

L'application ne connaît que ces abstractions : ni HTTP, ni SQL, ni FastAPI
(inversion de dépendance) — même principe que application/ports.py de
core_api.
"""

from abc import ABC, abstractmethod

from domain.entities import PowerFactorReading, Prediction, Recommendation, Site


class PredictionApiPort(ABC):
    """Accès à la prédiction de consommation d'un site, via le service Prediction."""

    @abstractmethod
    def get_prediction(self, site_id: str) -> Prediction | None:
        """Prédiction courante pour un site. Retourne None si indisponible."""


class SiteRepositoryPort(ABC):
    """Accès aux sites (capacité), tel que nécessaire aux règles métier."""

    @abstractmethod
    def get_site(self, site_id: str) -> Site | None:
        """Site par identifiant. Retourne None si inconnu ou incomplet."""


class PowerFactorRepositoryPort(ABC):
    """Accès au dernier facteur de puissance mesuré d'un site (readings_curated)."""

    @abstractmethod
    def get_latest_power_factor(self, site_id: str) -> PowerFactorReading | None:
        """Dernier facteur de puissance connu. Retourne None si indisponible."""


class RecommendationRepositoryPort(ABC):
    """Persistance des recommandations générées."""

    @abstractmethod
    def save(self, recommendations: list[Recommendation]) -> None:
        """Enregistre les recommandations. Aucun effet si la liste est vide."""
