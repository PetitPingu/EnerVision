"""Port (interface) que l'infrastructure doit implémenter.

L'application ne connaît que cette abstraction : elle ne dépend jamais de
`requests`, d'une URL HTTP ou de tout autre détail technique (inversion de
dépendance).
"""

from abc import ABC, abstractmethod

from domain.entities import Alert, AlertEvent, Reading, Site


class SensorApiPort(ABC):
    """Accès aux données de capteurs, quelle que soit la source réelle."""

    @abstractmethod
    def get_sites(self) -> list[Site]:
        """Liste des sites. Retourne [] si la source est indisponible."""

    @abstractmethod
    def get_current_reading(self, site_id: str) -> Reading | None:
        """Mesure instantanée d'un site. Retourne None si indisponible."""

    @abstractmethod
    def get_readings(
        self,
        site_id: str = None,
        start_time: str = None,
        end_time: str = None,
        limit: int = 100,
    ) -> list[Reading]:
        """Historique des lectures sur une période. Retourne [] si indisponible."""

    @abstractmethod
    def get_alerts(self, site_id: str = None, severity: str = None) -> list[Alert]:
        """Alertes de consommation actives. Retourne [] si indisponible."""

    @abstractmethod
    def get_sensors_status(self) -> dict:
        """État de santé des capteurs par site. Retourne {} si indisponible."""


class AlertStreamPort(ABC):
    """Accès au flux temps réel des transitions data_quality (Redis Streams)."""

    @abstractmethod
    async def read_new(self, last_id: str, block_ms: int) -> list[AlertEvent]:
        """Lit les entrées publiées après last_id (exclusif). Bloque jusqu'à
        block_ms millisecondes si rien de nouveau. Retourne [] au timeout ou
        si la source est indisponible — ne lève jamais."""


class ActiveAlertsPort(ABC):
    """Accès à l'état courant (pas au flux) des sites partial/degraded/critical."""

    @abstractmethod
    def get_active(self) -> list[AlertEvent]:
        """Snapshot des sites actuellement partial/degraded/critical (dernière
        lecture connue par site). Retourne [] si la source est indisponible."""
