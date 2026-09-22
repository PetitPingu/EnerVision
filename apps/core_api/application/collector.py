"""Cas d'usage : collecter la mesure courante de chaque site.

Ne dépend que du port SensorApiPort — jamais de l'implémentation concrète
(ApiMockClient), ce qui permet de tester ce cas d'usage sans réseau et de
changer de source de données sans toucher à cette classe.
"""

import logging

from domain.entities import Reading

from .ports import SensorApiPort

logger = logging.getLogger(__name__)


class SensorDataCollector:
    """Récupère la mesure courante de chaque site, via un SensorApiPort."""

    def __init__(self, api: SensorApiPort):
        self.api = api

    def collect_all(self) -> list[Reading]:
        """Collecte une mesure par site. Retourne la liste des lectures récupérées."""
        sites = self.api.get_sites()
        if not sites:
            logger.warning("Aucun site récupéré depuis l'API (indisponible ou vide).")
            return []

        readings: list[Reading] = []
        for site in sites:
            if not site.site_id:
                logger.error("Site reçu sans site_id, ignoré : %s", site)
                continue

            reading = self.api.get_current_reading(site.site_id)
            if reading is None:
                # Déjà loggé par l'implémentation du port ; on continue les autres sites.
                continue

            readings.append(reading)

        logger.info("Collecte terminée : %d lecture(s) récupérée(s).", len(readings))
        return readings
