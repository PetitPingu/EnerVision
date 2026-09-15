"""Réexporte le client de lecture de l'API Mock EnerVision.

Implémentation et tests de contrat : packages/mockapi-client (partagé avec
core_api). Voir DATA-02 / issue #16.
"""

from mockapi_client.mock_client import MockApiClient

__all__ = ["MockApiClient"]
