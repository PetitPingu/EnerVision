"""Connexion SQLAlchemy à la base PostgreSQL/TimescaleDB (moteur async, driver psycopg).

Package partagé : le schéma de base (tables, migrations Alembic) ne
dépend d'aucune app en particulier — plusieurs services peuvent s'y
brancher indépendamment, sans que l'un dépende du démarrage de l'autre.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import Config


class Base(DeclarativeBase):
    """Classe de base déclarative pour tous les modèles ORM du schéma partagé."""


engine = create_async_engine(Config.DATABASE_URL, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dépendance FastAPI : ouvre une session par requête et la ferme ensuite."""
    async with AsyncSessionLocal() as session:
        yield session
