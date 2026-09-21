# Test de charge — Locust

## Objectif

Vérifier que `core_api` encaisse un trafic concurrent réaliste (plusieurs
dashboards ouverts en même temps) sans dégradation excessive de latence,
avant une démo, une soutenance ou un déploiement.

## Périmètre : core_api uniquement

Le scénario ([apps/core_api/load-tests/locustfile.py](../apps/core_api/load-tests/locustfile.py))
ne cible que `core_api`, via Traefik — pas `prediction` ni `recommendation`
directement. C'est le point d'entrée unique du système
(dashboard → Traefik → core_api → services internes), donc le trajet le
plus représentatif d'un usage réel : appeler `prediction`/`recommendation`
en direct contournerait le proxy et les erreurs 5xx que `core_api` renvoie
quand un service en aval est indisponible (voir
[apps/core_api/presentation/api.py](../apps/core_api/presentation/api.py)).

`DashboardUser` reproduit le mélange d'appels que fait l'écran principal du
dashboard pour un site : lecture courante, historique, alertes actives,
état des capteurs, prédiction, recommandations. Les `site_id` sont
récupérés dynamiquement via `/api/v1/sites` au démarrage de chaque
utilisateur virtuel plutôt que codés en dur, l'API mock EnerVision ne
garantissant pas des identifiants stables.

## Déclenchement : manuel + nightly, jamais sur chaque push/PR

Contrairement à `prediction-tests.yml` ou `dashboard-e2e.yml`, le workflow
[.github/workflows/load-test.yml](../.github/workflows/load-test.yml) ne
tourne pas sur chaque push/PR : un test de charge construit toute la stack
docker compose (postgres, minio, mlflow, prediction, recommendation,
core_api, traefik) puis maintient une charge pendant 1 à plusieurs minutes,
ce qui est coûteux et bruyant sur des runners GitHub-hosted partagés à
capacité variable — un run mesuré à un instant donné n'est pas comparable
d'une exécution à l'autre. Il se déclenche :

- **à la demande** (`workflow_dispatch`), avec `users`, `spawn-rate` et
  `run-time` paramétrables depuis l'onglet Actions ;
- **automatiquement chaque nuit** (`schedule`, 02:00 UTC), pour repérer une
  dérive de perf dans le temps sans alourdir les PR.

## Résultat : informatif, ne fait jamais échouer la CI

Le run Locust (`continue-on-error: true`) ne fait jamais échouer le job,
quel que soit le taux d'erreur ou la latence observée. Aucun seuil de perf
fiable n'a encore été établi pour ce projet (pas de baseline de charge
en prod) ; fixer un seuil arbitraire aujourd'hui produirait un job rouge
sans signal exploitable. Le rapport (`report.html` + `report_*.csv`,
générés par `--csv`/`--html`) est publié comme artifact GitHub Actions
(rétention 14 jours) pour être consulté manuellement.

Piste d'évolution une fois une baseline connue : ajouter des seuils
(taux d'erreur, p95) lus depuis le CSV Locust en sortie de job, sur le
modèle des indicateurs de latence déjà suivis côté Traefik dans
[Monitoring](monitoring.md).

## Lancer en local

Stack docker compose démarrée (`docker compose up -d --build core_api traefik`) :

```bash
cd apps/core_api/load-tests
pip install -r requirements.txt

# UI interactive (http://localhost:8089)
locust -f locustfile.py --host http://localhost

# Headless, comme en CI
locust -f locustfile.py --host http://localhost \
    --users 20 --spawn-rate 5 --run-time 2m \
    --headless --csv=report --html=report.html
```
