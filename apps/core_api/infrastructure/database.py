"""Connexion SQLAlchemy à la base PostgreSQL/TimescaleDB (moteur async, driver psycopg).

Couche infrastructure : le domaine (domain/entities.py) reste des dataclasses
pures, sans dépendance SQL. Les modèles ORM mappés aux tables vivent dans
infrastructure/orm_models.py et ne sont utilisés qu'à cette couche.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import Config


class Base(DeclarativeBase):
    """Classe de base déclarative pour tous les modèles ORM de core-api."""


engine = create_async_engine(Config.DATABASE_URL, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dépendance FastAPI : ouvre une session par requête et la ferme ensuite."""
    async with AsyncSessionLocal() as session:
        yield session
