"""Port (interface) que l'infrastructure doit implémenter.

L'application ne connaît que cette abstraction : elle ne dépend jamais de
SQLAlchemy, psycopg ou de tout autre détail technique (inversion de
dépendance).
"""

from abc import ABC, abstractmethod

import pandas as pd


class TrainingDataPort(ABC):
    """Accès aux lectures consumption_readings pour l'entraînement ML."""

    @abstractmethod
    def fetch_training_data(self) -> pd.DataFrame:
        """Retourne les lectures prêtes pour features.build_features().

        Colonnes attendues : site_id, timestamp, consumption_kwh.
        Le filtre data_quality='good' est appliqué par l'implémentation.
        """
