"""Hachage de mot de passe et JWT (voir docs/seq_auth_token.md).

Fonctions pures, sans dépendance à FastAPI : la couche présentation s'en
sert pour construire la route /auth/login et la dépendance qui protège
les autres routes.
"""

import time

import bcrypt
import jwt

from .config import Config


def hash_password(password: str) -> str:
    """Hache un mot de passe en clair (bcrypt, jamais stocké tel quel)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe en clair contre son hash bcrypt."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject: str, **extra_claims: str | None) -> str:
    """Génère un JWT signé (exp courte), `sub` = email de l'utilisateur.

    `extra_claims` (ex. role, uid) est ajouté tel quel au payload — voir
    presentation/api.py:CurrentUser, qui en dépend pour éviter un aller-retour
    base à chaque requête (rôle admin, sites autorisés).
    """
    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + Config.JWT_EXPIRE_MINUTES * 60,
        **extra_claims,
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Vérifie signature + expiration, retourne le payload complet.

    Lève jwt.PyJWTError (ou une sous-classe) si le token est invalide ou expiré.
    """
    return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
