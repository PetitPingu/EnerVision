"""Point d'entrée : une collecte unique des données capteurs depuis l'API mock.

Composition root : c'est le seul endroit où l'on choisit l'implémentation
concrète (ApiMockClient) injectée dans le cas d'usage (SensorDataCollector).
"""

import logging

from application.collector import SensorDataCollector
from infrastructure.api_client import ApiMockClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    collector = SensorDataCollector(api=ApiMockClient())
    collector.collect_all()


if __name__ == "__main__":
    main()
