"""Scénario de charge Locust sur core_api.

Ne cible que core_api (voir docs/load-testing.md pour le choix de périmètre) 

Lancer en local (stack docker compose démarrée, Traefik sur :80) :
    locust -f locustfile.py --host http://localhost

Lancer en headless, comme dans la CI (voir .github/workflows/load-test.yml) :
    locust -f locustfile.py --host http://localhost \
        --users 20 --spawn-rate 5 --run-time 2m --headless \
        --csv=report --html=report.html
"""

import random
from datetime import datetime, timedelta, timezone

from locust import HttpUser, between, task

FALLBACK_SITE_IDS = ["SITE001"]


class DashboardUser(HttpUser):
    """Simule le mélange d'appels que fait l'écran principal du dashboard
    pour un site donné : lecture courante, historique, alertes, capteurs,
    prédiction, recommandations."""

    wait_time = between(1, 3)

    def on_start(self):
        response = self.client.get("/api/v1/sites", name="/api/v1/sites")
        sites = response.json() if response.ok else []
        self.site_ids = [s["site_id"] for s in sites] or FALLBACK_SITE_IDS

    def _site_id(self) -> str:
        return random.choice(self.site_ids)

    @task(5)
    def list_sites(self):
        self.client.get("/api/v1/sites", name="/api/v1/sites")

    @task(5)
    def current_reading(self):
        site_id = self._site_id()
        self.client.get(
            f"/api/v1/sites/{site_id}/current", name="/api/v1/sites/[site_id]/current"
        )

    @task(3)
    def readings_history(self):
        self.client.get(
            "/api/v1/readings",
            params={"site_id": self._site_id(), "limit": 100},
            name="/api/v1/readings",
        )

    @task(4)
    def active_alerts(self):
        self.client.get("/api/v1/alerts/active", name="/api/v1/alerts/active")

    @task(2)
    def sensors_status(self):
        self.client.get("/api/v1/sensors/status", name="/api/v1/sensors/status")

    @task(2)
    def predictions_range(self):
        now = datetime.now(timezone.utc)
        self.client.get(
            "/api/v1/predictions/range",
            params={
                "site_id": self._site_id(),
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=4)).isoformat(),
                "interval": "hour",
            },
            name="/api/v1/predictions/range",
        )

    @task(2)
    def recommendations(self):
        self.client.get(
            "/api/v1/recommendations",
            params={"site_id": self._site_id()},
            name="/api/v1/recommendations",
        )
