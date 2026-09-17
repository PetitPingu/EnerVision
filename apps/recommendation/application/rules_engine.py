"""Moteur de règles : évalue les règles métier à seuils pour un site.

Couche application : aucune dépendance HTTP/SQL, applique des règles pures
aux entités du domaine (Prediction, Site, PowerFactorReading) pour produire
des Recommendation. Règles documentées (cf. §10.2 du cahier des charges) :

1. Charge prédite > 90 % de capacity_kw -> décalage de charge, créneau cible
   hors pointe.
2. Pic prédit sur un créneau de pointe -> report de consommation vers un
   creux identifié.
3. power_factor < 0,90 -> compensation de l'énergie réactive.
"""

from collections.abc import Callable
from datetime import datetime

from domain.entities import PowerFactorReading, Prediction, Recommendation, Site

# Au-delà de 90% de sa capacité, un site risque le dépassement : on
# recommande un décalage de charge vers un créneau creux.
LOAD_SHIFT_THRESHOLD_RATIO = 0.9

# Créneau de pointe (heures pleines) : [8h, 20h). En dehors, le site est
# considéré en creux.
PEAK_HOURS_START = 8
PEAK_HOURS_END = 20
OFF_PEAK_TARGET_SLOT = "22h-6h"

# En-dessous de ce seuil, le facteur de puissance implique une pénalité
# d'énergie réactive : une compensation est recommandée.
POWER_FACTOR_THRESHOLD = 0.90


def _hour_of(target_timestamp: str | None) -> int | None:
    """Heure (UTC) du créneau cible, ou None si absent/invalide."""
    if target_timestamp is None:
        return None
    normalized = target_timestamp.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized).hour
    except ValueError:
        return None


def _load_shifting_rule(
    prediction: Prediction, site: Site, power_factor: PowerFactorReading | None
) -> Recommendation | None:
    """Consommation prédite supérieure à 90 % de la capacité du site -> décalage de charge."""
    threshold_kw = site.capacity_kw * LOAD_SHIFT_THRESHOLD_RATIO
    if prediction.predicted_consumption_kw <= threshold_kw:
        return None
    return Recommendation(
        site_id=site.site_id,
        type="load_shifting",
        message=(
            f"Consommation prédite ({prediction.predicted_consumption_kw:.1f} kWh) "
            f"supérieure à {LOAD_SHIFT_THRESHOLD_RATIO:.0%} de la capacité du site "
            f"({site.capacity_kw:.1f} kW) : décalage de charge recommandé vers le "
            f"créneau {OFF_PEAK_TARGET_SLOT}."
        ),
        model_version=prediction.model_version,
        estimated_gain_kwh=prediction.predicted_consumption_kw - threshold_kw,
    )


def _peak_shift_rule(
    prediction: Prediction, site: Site, power_factor: PowerFactorReading | None
) -> Recommendation | None:
    """Pic prédit sur le créneau de pointe -> report vers un creux identifié."""
    hour = _hour_of(prediction.target_timestamp)
    if hour is None or not (PEAK_HOURS_START <= hour < PEAK_HOURS_END):
        return None
    return Recommendation(
        site_id=site.site_id,
        type="peak_shift",
        message=(
            f"Pic de consommation prédit ({prediction.predicted_consumption_kw:.1f} kWh) "
            f"sur le créneau de pointe ({PEAK_HOURS_START}h-{PEAK_HOURS_END}h) : "
            f"report de consommation recommandé vers le creux identifié "
            f"({OFF_PEAK_TARGET_SLOT})."
        ),
        model_version=prediction.model_version,
        estimated_gain_kwh=prediction.predicted_consumption_kw,
    )


def _power_factor_compensation_rule(
    prediction: Prediction, site: Site, power_factor: PowerFactorReading | None
) -> Recommendation | None:
    """Facteur de puissance sous le seuil -> compensation de l'énergie réactive."""
    if power_factor is None or power_factor.power_factor >= POWER_FACTOR_THRESHOLD:
        return None
    return Recommendation(
        site_id=site.site_id,
        type="power_factor_compensation",
        message=(
            f"Facteur de puissance mesuré ({power_factor.power_factor:.2f}) "
            f"inférieur au seuil de {POWER_FACTOR_THRESHOLD:.2f} : compensation de "
            "l'énergie réactive recommandée."
        ),
        model_version=prediction.model_version,
        estimated_gain_kwh=None,
    )


_RULES: list[
    Callable[[Prediction, Site, PowerFactorReading | None], Recommendation | None]
] = [
    _load_shifting_rule,
    _peak_shift_rule,
    _power_factor_compensation_rule,
]


class RecommendationEngine:
    """Applique les règles métier à seuils et retourne les conseils déclenchés."""

    def evaluate(
        self,
        prediction: Prediction,
        site: Site,
        power_factor: PowerFactorReading | None = None,
    ) -> list[Recommendation]:
        """Une recommandation par règle déclenchée ; liste vide si aucune ne l'est."""
        return [
            recommendation
            for rule in _RULES
            if (recommendation := rule(prediction, site, power_factor)) is not None
        ]
