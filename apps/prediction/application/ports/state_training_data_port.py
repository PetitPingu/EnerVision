"""Port d'accès aux données d'entraînement du modèle d'état des capteurs."""

from abc import ABC, abstractmethod

import pandas as pd


class StateTrainingDataPort(ABC):
    """Accès aux lectures readings_curated pour l'entraînement du modèle de
    classification de l'état futur d'un capteur (data_quality)."""

    @abstractmethod
    def fetch_training_data(self) -> pd.DataFrame:
        """Retourne les lectures prêtes pour state_features.build_features().

        Colonnes attendues : site_id, timestamp, data_quality.
        Contrairement à TrainingDataPort (régression), les lignes ne sont
        pas filtrées sur consumption_kwh : data_quality est renseigné même
        pour une lecture critical/imputée.
        """
