"""Fixtures des tests d'intégration core_api : vrais Postgres et Redis.

Contrairement à `apps/core_api/tests/` (mocks/fakes sur les ports), ces
tests exercent les adapters SQL et Redis eux-mêmes. Lancer avant de les
jouer :

    docker compose up -d --wait postgres redis
    docker compose run --rm migrate

Un test qui ne trouve pas l'infra est skip (pas en échec) avec un message
expliquant comment la démarrer, plutôt qu'une pile d'exceptions SQLAlchemy.
"""

import redis
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from infrastructure.config import Config
from infrastructure.session import engine as core_api_engine


@pytest.fixture(scope="session", autouse=True)
def _require_postgres():
    try:
        with core_api_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"Postgres injoignable ({exc}) - lancer `docker compose up -d --wait postgres` puis `docker compose run --rm migrate`")


@pytest.fixture
def redis_client():
    client = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)
    try:
        client.ping()
    except redis.exceptions.ConnectionError as exc:
        pytest.skip(f"Redis injoignable ({exc}) - lancer `docker compose up -d --wait redis`")
    yield client
    client.close()
