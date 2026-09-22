"""Lecteur mock des données d'entraînement du modèle d'état (en attendant
Postgres).

Simule le résultat d'une requête SQL sur readings_curated
(colonnes site_id / timestamp / data_quality) : plusieurs lectures par
heure et par site (comme readings_curated, une par minute), toutes
cohérentes entre elles pour une même heure - nécessaire pour que
aggregate_hourly() (MIN_OFF_READINGS_PER_HOUR) retienne les pannes au lieu
de les rejeter comme du bruit.
"""

import pandas as pd

from application.ports import StateTrainingDataPort
from infrastructure.ml.state.features import RAW_COLUMNS, SENSOR_COLUMNS

# Plusieurs lectures par (site, heure), comme readings_curated (une par
# minute) - au-dessus de MIN_OFF_READINGS_PER_HOUR pour que les pannes
# soient retenues après aggregate_hourly(), pas rejetées comme du bruit.
_READINGS_PER_HOUR = [5, 25, 45]
_HOURS = range(8, 20)
_SITE_COUNT = 7


class MockStateTrainingDataReader(StateTrainingDataPort):
    """Retourne des lectures synthétiques pour développer sans base de données."""

    def fetch_training_data(self) -> pd.DataFrame:
        rows = []
        for site_num in range(1, _SITE_COUNT + 1):
            for hour in _HOURS:
                # Corrélé (par palier d'heure, pas modulo - un arbre de
                # décision apprend des seuils, pas une périodicité) pour
                # que le pattern soit apprenable - voir test_state_trainer.py.
                state = _state_for_hour(hour)
                for minute in _READINGS_PER_HOUR:
                    rows.append(
                        {
                            "site_id": f"SITE00{site_num}",
                            "timestamp": f"2026-09-07T{hour:02d}:{minute:02d}:00",
                            "data_quality": state,
                            **_sensor_values(state),
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
