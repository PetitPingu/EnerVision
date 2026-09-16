"""Ports (interfaces) que l'infrastructure doit implémenter.

L'application ne connaît que ces abstractions : elle ne dépend jamais de
SQLAlchemy, psycopg, MinIO ou de tout autre détail technique (inversion de
dépendance).
"""

from application.ports.model_store_port import ModelStorePort, SavedModelMetadata
from application.ports.training_data_port import TrainingDataPort

__all__ = [
    "ModelStorePort",
    "SavedModelMetadata",
    "TrainingDataPort",
]
