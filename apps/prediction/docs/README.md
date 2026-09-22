# Service Prediction — documentation

Documentation du service `apps/prediction` : prédiction de consommation
énergétique à partir des lectures curées par l'ETL.

## Contenu

| Document | Description |
|---|---|
| [architecture.md](architecture.md) | Architecture hexagonale, couches, ports, flux de données |
| [ml-pipeline.md](ml-pipeline.md) | Feature engineering, modèle sklearn, métriques |
| [model-choice.md](model-choice.md) | Justification du choix RandomForestRegressor |
| [state-model.md](state-model.md) | Second modèle (état on/off de chaque capteur) : package, entraînement, endpoint `/predict/state` |
| [model-registry.md](model-registry.md) | `MlflowModelStore` : enregistrement dans le Model Registry MLflow |
| [configuration.md](configuration.md) | Variables d'environnement |
| [development.md](development.md) | Lancer en local, tests, CI, scripts manuels |

## Périmètre de cette PR (phase 1)

- Scaffold FastAPI (`/health`)
- Pipeline ML (entraînement + évaluation MAE/RMSE)
- Lecture des données via `TrainingDataPort` (mock, JSON, Postgres)
- Persistance du modèle via `ModelStorePort` (MinIO)
- Use case `train_and_publish`
- 15 tests unitaires + workflow GitHub Actions

**Hors périmètre (phase 2) :** endpoint `/predict`, chargement du modèle en
mémoire au démarrage, cron APScheduler, MLflow, écriture table `PREDICTIONS`.

## Liens utiles

- Worker ETL et table `readings_curated` : [docs/ingestion-worker.md](../../../docs/ingestion-worker.md)
- Architecture infra globale : [docs/archi_infra.md](../../../docs/archi_infra.md)
- Séquence cible (MLflow) : [docs/seq_prediction.md](../../../docs/seq_prediction.md)
