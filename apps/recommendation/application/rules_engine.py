"""Moteur de règles : évalue les règles métier à seuils pour un site.

Couche application : aucune dépendance HTTP/SQL, applique des règles pures
aux entités du domaine (Prediction, Site) pour produire des Recommendation.
"""

from collections.abc import Callable

from domain.entities import Prediction, Recommendation, Site

# Au-delà de 100% de sa capacité, un site est en dépassement : on recommande
# un effacement de charge (load shedding).
LOAD_SHEDDING_THRESHOLD_RATIO = 1.0


def _load_shedding_rule(prediction: Prediction, site: Site) -> Recommendation | None:
    """Consommation prédite supérieure à la capacité du site → délestage."""
    threshold_kw = site.capacity_kw * LOAD_SHEDDING_THRESHOLD_RATIO
    if prediction.predicted_consumption_kw <= threshold_kw:
        return None
    return Recommendation(
        site_id=site.site_id,
        type="load_shedding",
        message=(
            f"Consommation prédite ({prediction.predicted_consumption_kw:.1f} kW) "
            f"supérieure à la capacité du site ({site.capacity_kw:.1f} kW) : "
            "effacement de charge recommandé."
        ),
    )


_RULES: list[Callable[[Prediction, Site], Recommendation | None]] = [_load_shedding_rule]


class RecommendationEngine:
    """Applique les règles métier à seuils et retourne les conseils déclenchés."""

    def evaluate(self, prediction: Prediction, site: Site) -> list[Recommendation]:
        """Une recommandation par règle déclenchée ; liste vide si aucune ne l'est."""
        return [
            recommendation
            for rule in _RULES
            if (recommendation := rule(prediction, site)) is not None
        ]
