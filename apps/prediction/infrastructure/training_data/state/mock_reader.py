"""Lecteur mock des données d'entraînement du modèle d'état (en attendant
Postgres).

Simule le résultat d'une requête SQL sur readings_curated
(colonnes site_id / timestamp / data_quality).
"""

import pandas as pd

from application.ports import StateTrainingDataPort
from infrastructure.ml.state.features import RAW_COLUMNS, SENSOR_COLUMNS


class MockStateTrainingDataReader(StateTrainingDataPort):
    """Retourne des lectures synthétiques pour développer sans base de données."""

    def fetch_training_data(self) -> pd.DataFrame:
        rows = []
        for i in range(40):
            site_num = (i % 7) + 1
            hour = 8 + (i % 12)
            minute = (i * 7) % 60
            rows.append(
                {
                    "site_id": f"SITE00{site_num}",
                    "timestamp": f"2026-09-07T{hour:02d}:{minute:02d}:00",
                    # Corrélé (par palier d'heure, pas modulo - un arbre de
                    # décision apprend des seuils, pas une périodicité) pour
                    # que le pattern soit apprenable - voir test_state_trainer.py.
                    "data_quality": _state_for_hour(hour),
                    **_sensor_values(_state_for_hour(hour)),
                }
            )
        return pd.DataFrame(rows, columns=RAW_COLUMNS)


def _state_for_hour(hour: int) -> str:
    if hour < 11:
        return "critical"
    if hour < 14:
        return "degraded"
    if hour < 17:
        return "partial"
    return "good"


# Capteurs off par état : aucun pour good, tous pour critical, pannes
# partielles entre les deux (cohérent avec ce qu'on observe en base).
_OFF_SENSORS = {
    "good": [],
    "partial": ["humidity_percent"],
    "degraded": ["consumption_kw", "power_factor"],
    "critical": SENSOR_COLUMNS,
}


def _sensor_values(state: str) -> dict:
    off = _OFF_SENSORS[state]
    return {name: None if name in off else 1.0 for name in SENSOR_COLUMNS}
