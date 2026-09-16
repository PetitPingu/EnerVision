"""Port d'accès aux données d'entraînement."""

from abc import ABC, abstractmethod

import pandas as pd


class TrainingDataPort(ABC):
    """Accès aux lectures readings_curated pour l'entraînement ML."""

    @abstractmethod
    def fetch_training_data(self) -> pd.DataFrame:
        """Retourne les lectures prêtes pour features.build_features().

        Colonnes attendues : site_id, timestamp, consumption_kwh.
        Les lignes sans consumption_kwh sont exclues par l'implémentation.
        """
