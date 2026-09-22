"""Fixtures des tests d'intégration etl_worker : vrais Postgres, Redis et MinIO.

Contrairement à `apps/etl_worker/tests/` (mocks/fakes sur les ports), ces
tests exercent les adapters SQL/Redis/MinIO eux-mêmes. Lancer avant de les
jouer :

    docker compose up -d --wait postgres redis minio
    docker compose run --rm minio-init
    docker compose run --rm migrate

Un test qui ne trouve pas l'infra est skip (pas en échec) avec un message
expliquant comment la démarrer.
"""

import redis
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
def redis_client():
    client = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)
    try:
        client.ping()
    except redis.exceptions.ConnectionError as exc:
        pytest.skip(f"Redis injoignable ({exc}) - lancer `docker compose up -d --wait redis`")
    yield client
    client.close()


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
        exists = client.bucket_exists(Config.MINIO_RAW_BUCKET)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"MinIO injoignable ({exc}) - lancer `docker compose up -d --wait minio`")
    if not exists:
        pytest.skip(
            f"Bucket {Config.MINIO_RAW_BUCKET} absent - lancer `docker compose run --rm minio-init`"
        )
    return client
