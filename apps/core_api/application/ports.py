"""Port (interface) que l'infrastructure doit implémenter.

L'application ne connaît que cette abstraction : elle ne dépend jamais de
`requests`, d'une URL HTTP ou de tout autre détail technique (inversion de
dépendance).
"""

from abc import ABC, abstractmethod

from domain.entities import Alert, AlertEvent, Reading, Site, User


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


class UserRepositoryPort(ABC):
    """Accès aux comptes utilisateurs, quelle que soit la source réelle."""

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Utilisateur correspondant à cet email. Retourne None si inconnu."""

    @abstractmethod
    def get_by_id(self, user_id: str) -> User | None:
        """Utilisateur correspondant à cet id. Retourne None si inconnu."""

    @abstractmethod
    def list_all(self) -> list[User]:
        """Tous les comptes utilisateurs (page admin)."""

    @abstractmethod
    def create(self, email: str, password_hash: str, role: str | None) -> User:
        """Crée un utilisateur. Lève ValueError si l'email existe déjà."""

    @abstractmethod
    def update_role(self, user_id: str, role: str | None) -> User | None:
        """Met à jour le rôle. Retourne None si l'utilisateur est inconnu."""

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Supprime l'utilisateur. Retourne False s'il était déjà inconnu."""


class SiteAccessPort(ABC):
    """Sites qu'un utilisateur (non-admin) est autorisé à voir.

    Le rôle admin contourne cette table (voir presentation/api.py) : elle
    ne concerne que les comptes non-admin.
    """

    @abstractmethod
    def get_site_ids(self, user_id: str) -> list[str]:
        """Sites assignés à cet utilisateur."""

    @abstractmethod
    def set_site_ids(self, user_id: str, site_ids: list[str]) -> None:
        """Remplace l'ensemble des sites assignés à cet utilisateur."""


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


class LatestReadingsPort(ABC):
    """Dernière lecture connue par site, lue dans notre base (readings_curated) —
    pas un relais à l'API mock (contrairement à SensorApiPort.get_current_reading,
    qui interroge l'API mock en direct)."""

    @abstractmethod
    def get_latest(self) -> list[Reading]:
        """Dernière lecture de chaque site, toutes qualités confondues
        (good compris, contrairement à ActiveAlertsPort). Retourne [] si la
        source est indisponible."""
