"""Cas d'usage : générer les recommandations d'un site.

Couche application : orchestre les ports (Prediction, Site, persistance) et
le moteur de règles (rules_engine), sans connaître leurs implémentations
concrètes — même principe que collector.py dans core_api.
"""

from domain.entities import Recommendation

from .ports import (
    PowerFactorRepositoryPort,
    PredictionApiPort,
    RecommendationRepositoryPort,
    SiteRepositoryPort,
)
from .rules_engine import RecommendationEngine


class GenerateRecommendations:
    """Récupère la prédiction et le site, applique les règles, persiste le résultat."""

    def __init__(
        self,
        prediction_api: PredictionApiPort,
        site_repository: SiteRepositoryPort,
        power_factor_repository: PowerFactorRepositoryPort,
        recommendation_repository: RecommendationRepositoryPort,
        engine: RecommendationEngine | None = None,
    ):
        self._prediction_api = prediction_api
        self._site_repository = site_repository
        self._power_factor_repository = power_factor_repository
        self._recommendation_repository = recommendation_repository
        self._engine = engine or RecommendationEngine()

    def execute(self, site_id: str) -> list[Recommendation] | None:
        """Recommandations déclenchées pour ce site, ou None si site/prédiction indisponible."""
        site = self._site_repository.get_site(site_id)
        if site is None:
            return None
        prediction = self._prediction_api.get_prediction(site_id)
        if prediction is None:
            return None
        power_factor = self._power_factor_repository.get_latest_power_factor(site_id)
        recommendations = self._engine.evaluate(prediction, site, power_factor)
        self._recommendation_repository.save(recommendations)
        return recommendations
