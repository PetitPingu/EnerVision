"""Session SQLAlchemy synchrone vers la base partagée (packages/db-schema).

Session synchrone : core_api reste par ailleurs asynchrone (FastAPI, route SSE),
mais ce point de lecture est un one-shot par requête HTTP, pas un flux — pas
besoin d'un moteur async pour ça (même choix que apps/recommendation).
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
