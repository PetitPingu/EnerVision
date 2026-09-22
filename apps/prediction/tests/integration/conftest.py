"""Fixtures des tests d'intégration prediction : vrais Postgres et MinIO.

Contrairement au reste de tests/ (mocks/fakes sur les ports), ces tests
exercent PostgresTrainingDataReader et MinioModelStore contre l'infra
réelle (pas MlflowModelStore : nécessiterait en plus un serveur MLflow,
hors scope de cette suite). Lancer avant de les jouer :

    docker compose up -d --wait postgres minio
    docker compose run --rm minio-init
    docker compose run --rm migrate

Un test qui ne trouve pas l'infra est skip (pas en échec) avec un message
expliquant comment la démarrer.
"""

import pytest
from minio import Minio
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from infrastructure.config import Config


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(Config.DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(
            f"Postgres injoignable ({exc}) - lancer `docker compose up -d --wait postgres` "
            "puis `docker compose run --rm migrate`"
        )
    yield engine
    engine.dispose()


@pytest.fixture
def minio_client():
    client = Minio(
        Config.MINIO_ENDPOINT,
        access_key=Config.MINIO_ACCESS_KEY,
        secret_key=Config.MINIO_SECRET_KEY,
        secure=Config.MINIO_SECURE,
    )
    try:
        # Simple garde de connectivité : n'importe quelle erreur MinIO ici
        # (connexion refusée, DNS...) signifie que l'infra n'est pas prête.
        exists = client.bucket_exists(Config.MINIO_MODELS_BUCKET)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"MinIO injoignable ({exc}) - lancer `docker compose up -d --wait minio`")
    if not exists:
        pytest.skip(
            f"Bucket {Config.MINIO_MODELS_BUCKET} absent - lancer `docker compose run --rm minio-init`"
        )
    return client
