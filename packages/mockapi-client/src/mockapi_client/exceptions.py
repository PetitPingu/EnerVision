"""Exceptions du client de l'API Mock.

Toute erreur est remontée à l'appelant sous une de ces formes dédiées : ce
module ne masque jamais un échec derrière une valeur par défaut (voir
mock_client.py). C'est à l'appelant de décider comment réagir.
"""


class MockApiError(Exception):
    """Erreur générique lors d'un appel à l'API Mock."""


class MockApiTimeoutError(MockApiError):
    """La requête a dépassé le délai imparti, même après les tentatives de retry."""


class MockApiConnectionError(MockApiError):
    """Impossible de joindre l'API Mock (réseau, DNS, connexion refusée)."""


class MockApiHTTPError(MockApiError):
    """Réponse HTTP en erreur (4xx/5xx) après épuisement des tentatives éventuelles."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)


class MockApiNotFoundError(MockApiHTTPError):
    """Ressource introuvable (404) — ex : site_id inconnu."""

    def __init__(self, message: str):
        super().__init__(404, message)


class MockApiValidationError(MockApiHTTPError):
    """Requête rejetée par l'API (422) — paramètres invalides."""

    def __init__(self, message: str):
        super().__init__(422, message)
