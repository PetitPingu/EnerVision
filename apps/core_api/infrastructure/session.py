"""Session SQLAlchemy synchrone vers la base partagée (packages/db-schema).

Session synchrone plutôt que le moteur async de db_schema.database : les
routes FastAPI de ce service sont toutes en `def` (pas `async def`), même
raisonnement que apps/recommendation/infrastructure/session.py.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from db_schema.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = create_engine(Config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session() -> Iterator[Session]:
    """Ouvre une session, la annule en cas d'erreur puis la ferme."""
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
