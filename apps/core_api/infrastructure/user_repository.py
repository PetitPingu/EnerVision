"""Implémentation SQL du UserRepositoryPort (table `users`, packages/db-schema)."""

import uuid

from application.ports import UserRepositoryPort
from db_schema.models import User as UserRow
from domain.entities import User
from sqlalchemy.exc import IntegrityError

from .session import get_session


def _to_domain(row: UserRow) -> User:
    return User(
        id=str(row.id),
        email=row.email,
        password_hash=row.password_hash,
        role=row.role,
    )


class SqlUserRepository(UserRepositoryPort):
    """Lit/écrit les comptes utilisateurs dans la base partagée."""

    def get_by_email(self, email: str) -> User | None:
        with get_session() as session:
            row = session.query(UserRow).filter(UserRow.email == email).one_or_none()
        return None if row is None else _to_domain(row)

    def get_by_id(self, user_id: str) -> User | None:
        with get_session() as session:
            row = session.get(UserRow, uuid.UUID(user_id))
        return None if row is None else _to_domain(row)

    def list_all(self) -> list[User]:
        with get_session() as session:
            rows = session.query(UserRow).order_by(UserRow.email).all()
        return [_to_domain(row) for row in rows]

    def create(self, email: str, password_hash: str, role: str | None) -> User:
        row = UserRow(id=uuid.uuid4(), email=email, password_hash=password_hash, role=role)
        try:
            with get_session() as session:
                session.add(row)
                session.commit()
                session.refresh(row)
                return _to_domain(row)
        except IntegrityError as exc:
            raise ValueError(f"Un utilisateur existe déjà avec l'email {email}") from exc

    def update_role(self, user_id: str, role: str | None) -> User | None:
        with get_session() as session:
            row = session.get(UserRow, uuid.UUID(user_id))
            if row is None:
                return None
            row.role = role
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def delete(self, user_id: str) -> bool:
        with get_session() as session:
            row = session.get(UserRow, uuid.UUID(user_id))
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
