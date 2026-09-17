# Configuration

Le service lit les variables d'environnement via `python-dotenv`
(`infrastructure/config.py`). Le fichier `.env` à la **racine du monorepo**
est partagé avec les autres services (ETL, core_api).

Voir aussi `apps/prediction/.env.example` pour les variables spécifiques
au service.

## Variables du service

| Variable | Défaut | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://...` | Connexion Postgres (`readings_curated`) |
| `PREDICTION_PORT` | `8000` | Port HTTP (8002 en local hors Docker) |
| `TRAINING_DATA_SOURCE` | `mock` | `mock` \| `json` \| `postgres` |
| `TRAINING_DATA_JSON_PATH` | — | Chemin JSON si `source=json` |
| `MODEL_STORE` | `minio` | Backend de persistance (`minio` pour l'instant) |
| `MODEL_NAME` | `energy-consumption` | Préfixe des clés objet MinIO |

## Variables MinIO (partagées avec l'ETL)

Définies dans le `.env` racine :

| Variable | Description |
|---|---|
| `MINIO_ENDPOINT` | Hôte:port (ex. `10.101.200.36:9000` ou `localhost:9000`) |
| `MINIO_ROOT_USER` | Access key |
| `MINIO_ROOT_PASSWORD` | Secret key |
| `MINIO_MODELS_BUCKET` | Bucket des modèles (`models`) |
| `MINIO_SECURE` | `true` si HTTPS (défaut : `false`) |

> En Docker, `docker-compose.yml` injecte `MINIO_ENDPOINT=minio:9000` pour
> le service prediction. En local hors Docker, pointer vers le serveur
> externe (même IP que `DATABASE_URL`).

## Exemple `.env` racine (extrait)

```env
DATABASE_URL=postgresql+psycopg://enervision:***@10.101.200.36:5432/enervision
TRAINING_DATA_SOURCE=postgres

MINIO_ENDPOINT=10.101.200.36:9000
MINIO_ROOT_USER=enervision
MINIO_ROOT_PASSWORD=***
MINIO_MODELS_BUCKET=models
```

## Docker Compose

Le service `prediction` reçoit :

```yaml
DATABASE_URL: postgresql+psycopg://...@postgres:5432/enervision
TRAINING_DATA_SOURCE: postgres
MODEL_STORE: minio
MODEL_NAME: energy-consumption
MINIO_ENDPOINT: minio:9000
MINIO_MODELS_BUCKET: models
```
