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
| `MODEL_STORE` | `minio` | Backend de persistance : `minio` \| `mlflow` |
| `MODEL_NAME` | `energy-consumption` | Préfixe des clés objet MinIO, et nom du modèle dans le Model Registry MLflow |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | Serveur MLflow, utilisé si `MODEL_STORE=mlflow` |

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

## Variables MLflow (si `MODEL_STORE=mlflow`)

`MlflowModelStore` parle au serveur MLflow (`MLFLOW_TRACKING_URI`) pour le
tracking et le Model Registry, **et directement à MinIO** pour lire/écrire
les artefacts - le tracking server ne les proxie pas. Mêmes identifiants
MinIO que ci-dessus, plus :

| Variable | Description |
|---|---|
| `MLFLOW_S3_ENDPOINT_URL` | Endpoint MinIO pour le client MLflow (`http://minio:9000` en Docker) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | = `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` (boto3 ne connaît pas les noms MinIO) |
| `AWS_DEFAULT_REGION` | Requis par boto3 même hors AWS (`us-east-1`) |
| `AWS_CONFIG_FILE` | Pointe vers `aws_config` (addressing style "path", sinon boto3 essaie de résoudre `models.minio:9000` en DNS) |

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
MODEL_STORE: minio  # ou "mlflow"
MODEL_NAME: energy-consumption
MINIO_ENDPOINT: minio:9000
MINIO_MODELS_BUCKET: models
# Utilisées seulement si MODEL_STORE=mlflow (voir section ci-dessus) :
MLFLOW_TRACKING_URI: http://mlflow:5000
MLFLOW_S3_ENDPOINT_URL: http://minio:9000
AWS_DEFAULT_REGION: us-east-1
AWS_CONFIG_FILE: /app/aws_config
```
