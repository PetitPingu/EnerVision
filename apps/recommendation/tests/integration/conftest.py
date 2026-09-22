"""Fixtures des tests d'intégration recommendation : vrai Postgres.

Contrairement à `apps/recommendation/tests/` (mocks/fakes sur les ports),
ces tests exercent les repositories SQL eux-mêmes. Lancer avant de les
jouer :

    docker compose up -d --wait postgres
    docker compose run --rm migrate

Un test qui ne trouve pas l'infra est skip (pas en échec) avec un message
expliquant comment la démarrer.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from infrastructure.session import engine as recommendation_engine


@pytest.fixture(scope="session", autouse=True)
def _require_postgres():
    try:
        with recommendation_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(
            f"Postgres injoignable ({exc}) - lancer `docker compose up -d --wait postgres` "
            "puis `docker compose run --rm migrate`"
        )
