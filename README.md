# EnerVision

Plateforme de suivi, prédiction et recommandation de consommation
énergétique pour des sites industriels : ingestion des relevés capteurs,
détection de la qualité des données, prédiction de consommation (ML) et
recommandations d'optimisation à seuils, exposées via un dashboard web.

## Architecture en un coup d'œil

Monorepo de 4 services Python (FastAPI, architecture hexagonale
`domain/application/infrastructure/presentation`) + 1 dashboard Next.js,
orchestrés via Docker Compose derrière Traefik :

| Service | Rôle |
|---|---|
| `core_api` | Point d'entrée (BFF) du dashboard, agrège Prediction + Recommendation + l'API mock EnerVision |
| `prediction` | Sert le modèle ML (`/predict`, `/predict/range`) et le réentraîne périodiquement (MLflow) |
| `recommendation` | Applique des règles à seuils sur les prédictions et persiste les recommandations |
| `etl_worker` | Ingère les relevés de l'API mock en continu, écrit le brut dans MinIO et cure dans TimescaleDB |
| `dashboard` | Interface Next.js/React — **ne tourne pas dans `docker-compose.yml`**, à lancer séparément (voir plus bas) |

Stockage : TimescaleDB (PostgreSQL) pour les données structurées, MinIO
(S3-compatible) pour le data lake brut et l'artifact store MLflow.
Monitoring : Prometheus + Grafana. Détail complet et diagrammes dans
[docs/archi_infra.md](docs/archi_infra.md).

> Aucune authentification n'est implémentée à ce jour sur les API (voir
> [docs/seq_auth_token.md](docs/seq_auth_token.md)) — à garder en tête avant
> tout déploiement au-delà de la démo.

## Prérequis

- Docker + Docker Compose (plugin `docker compose`)
- Python 3.12
- Node.js 22

## Démarrage rapide

1. Créer un `.env` à la racine du repo (aucun `.env.example` n'est
   versionné — voir la liste des variables attendues dans
   `docker-compose.yml` et dans le `infrastructure/config.py` de chaque
   service ; les valeurs par défaut de démo utilisent `changeme*`, à ne
   jamais garder en prod).

2. Lancer l'infra + les services backend :

   ```bash
   docker compose up -d
   ```

   `core_api` et `recommendation` appliquent automatiquement les
   migrations Alembic (`packages/db-schema`) au démarrage — le schéma
   existe dès ce premier `up`.

3. Lancer le dashboard séparément (pas dans `docker-compose.yml`) :

   ```bash
   cd apps/dashboard
   npm install
   npm run dev
   ```

   Ouvrir http://localhost:3000.

Sous Windows, `scripts/install-deps.bat` (installe les dépendances Python
des 3 services API + les dépendances npm du dashboard) et
`scripts/start-dev.bat` (lance migrations + core_api + prediction +
recommendation + dashboard en local, hors Docker, avec rechargement à
chaud) automatisent ce flux pour le développement au jour le jour.
`etl_worker` n'est volontairement pas inclus dans ces scripts : il a
besoin de Postgres/MinIO déjà debout — voir
[docs/ingestion-worker.md](docs/ingestion-worker.md) pour le lancer.

Chaque service Python installe ses dépendances partagées
(`packages/db-schema`, `packages/mockapi-client`) automatiquement via
`pip install -r requirements.txt` (dépendances éditables en chemin
relatif) — pas d'étape d'installation séparée pour `packages/`.

## Vérifier que ça tourne

| URL | Attendu |
|---|---|
| http://localhost:8001/docs (ou via Traefik, voir `docker-compose.yml`) | Swagger `core_api` |
| http://localhost:3000 | Dashboard |
| http://localhost:9001 | Console MinIO |
| http://localhost:5000 | UI MLflow |
| http://grafana.localhost (via Traefik, voir [docs/monitoring.md](docs/monitoring.md)) | Dashboard infra "EnerVision - Vue d'ensemble" |

## Structure du repo

```
apps/            core_api, prediction, recommendation, etl_worker, dashboard
packages/        db-schema (modèles + migrations Alembic), mockapi-client (client API mock partagé)
docs/            architecture, schéma DB, diagrammes de séquence
monitoring/      config Prometheus + provisioning Grafana
scripts/         scripts de dev Windows (.bat)
```

## Documentation

| Doc | Contenu |
|---|---|
| [docs/archi_infra.md](docs/archi_infra.md) | Vue d'ensemble infra + diagramme |
| [docs/archi_database.md](docs/archi_database.md) | Schéma PostgreSQL (tables implémentées vs proposées) |
| [docs/data-storage.md](docs/data-storage.md) | Socle TimescaleDB + MinIO |
| [docs/ingestion-worker.md](docs/ingestion-worker.md) | Worker ETL (ingestion + curation) |
| [docs/monitoring.md](docs/monitoring.md) | Prometheus + Grafana |
| [docs/seq_etl.md](docs/seq_etl.md), [seq_predict_call.md](docs/seq_predict_call.md), [seq_prediction.md](docs/seq_prediction.md) | Diagrammes de séquence des flux implémentés |
| [docs/seq_auth_token.md](docs/seq_auth_token.md) | Design d'authentification **proposé, non implémenté** |
| [apps/prediction/docs/](apps/prediction/docs/) | Architecture, pipeline ML et Model Registry détaillés du service Prediction |

## Tests & CI

Chaque service Python a sa propre suite `pytest` (`apps/<service>/tests/`).
Seul `apps/prediction` a un workflow CI dédié
([.github/workflows/prediction-tests.yml](.github/workflows/prediction-tests.yml)) ;
`core_api`, `etl_worker` et `recommendation` sont couverts par Trivy (scan
de vulnérabilités) mais pas par une exécution automatique de leurs tests —
les lancer manuellement avant de merger :

```bash
cd apps/<service>
python -m pytest -v
```

Le dashboard a son lint, son build et ses tests e2e Playwright en CI
(`.github/workflows/dashboard-*.yml`).
