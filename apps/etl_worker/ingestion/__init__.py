"""Ingestion des données de l'API Mock EnerVision.

L'implémentation et les tests de contrat vivent dans le package partagé
`mockapi-client` (packages/mockapi-client), utilisé aussi par core_api,
pour garantir un seul point d'appel à l'API mock dans tout le monorepo.
Ce package ré-exporte simplement ce dont l'ETL worker a besoin.
"""

from mockapi_client import (
    Alert,
    EnergyReading,
    MockApiClient,
    MockApiConnectionError,
    MockApiError,
    MockApiHTTPError,
    MockApiNotFoundError,
    MockApiTimeoutError,
    MockApiValidationError,
    Site,
)

__all__ = [
    "MockApiClient",
    "Site",
    "EnergyReading",
    "Alert",
    "MockApiError",
    "MockApiTimeoutError",
    "MockApiConnectionError",
    "MockApiHTTPError",
    "MockApiNotFoundError",
    "MockApiValidationError",
]
