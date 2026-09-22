"""Vérifie que le module ingestion expose bien le client partagé mockapi-client.

Les tests de contrat du client lui-même (les 4 niveaux de data_quality,
retry/backoff, raw_payload, etc.) vivent dans packages/mockapi-client/tests
— pas dupliqués ici.
"""

from ingestion import EnergyReading, MockApiClient, Site
from ingestion.mock_client import MockApiClient as MockApiClientFromSubmodule


def test_ingestion_reexports_mock_api_client():
    assert MockApiClient is MockApiClientFromSubmodule


def test_ingestion_reexports_models():
    assert Site.__name__ == "Site"
    assert EnergyReading.__name__ == "EnergyReading"
