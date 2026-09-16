# Développement local

## Prérequis

- Python 3.12+
- Accès Postgres (`readings_curated` alimentée par l'ETL)
- Accès MinIO (bucket `models`) pour la publication de modèle

## Installation

```bash
cd apps/prediction
pip install -r requirements-dev.txt
```

Installe aussi `packages/db-schema` en editable (`-e ../../packages/db-schema`).

## Lancer l'API

```bash
cd apps/prediction
python main.py
# → http://127.0.0.1:8002/health
```

## Tests

```bash
cd apps/prediction
python -m pytest tests/ -q
```

### Organisation des tests

```
tests/
├── api/              # Endpoints FastAPI
├── ml/               # features, pipeline, trainer
├── training_data/    # Lecteurs mock/json/postgres
├── model_store/      # MinioModelStore
├── application/      # Use case train_and_publish
└── manual/           # Scripts manuels (non collectés par pytest)
```

15 tests unitaires. Le workflow CI
[`.github/workflows/prediction-tests.yml`](../../../.github/workflows/prediction-tests.yml)
les exécute sur chaque push/PR vers `main` ou `dev`.

## Scripts manuels

### Explorer les données Postgres + entraîner (sans MinIO)

```bash
cd apps/prediction
python tests/manual/manual_postgres_train.py
```

Affiche stats, features, métriques MAE/RMSE et prédictions sur 5 lignes.

### Entraîner et publier dans MinIO

```bash
cd apps/prediction
python tests/manual/manual_train_and_publish.py
```

Enchaîne : `create_training_data_reader()` → `train_and_publish()` →
`MinioModelStore.save()`.

Variables requises dans le `.env` racine :
`DATABASE_URL`, `TRAINING_DATA_SOURCE=postgres`, `MINIO_*`.

## Docker

```bash
# Depuis la racine du monorepo
docker compose up -d prediction
```

Le Dockerfile utilise le contexte racine pour copier `packages/db-schema`.

## Dépannage MinIO

| Erreur | Cause probable | Solution |
|---|---|---|
| `InvalidAccessKeyId` | `MINIO_ENDPOINT` pointe vers localhost au lieu du serveur externe | Aligner sur l'IP du serveur (comme `DATABASE_URL`) |
| `NoSuchBucket` | Bucket `models` absent | Créer le bucket ou lancer `minio-init` |
| `Source donnees : mock` | `TRAINING_DATA_SOURCE` absent du `.env` | Ajouter `TRAINING_DATA_SOURCE=postgres` |
