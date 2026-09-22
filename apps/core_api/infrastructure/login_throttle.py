"""Limitation des tentatives de connexion (voir ANSSI-PG-078) : sans ce
type de mesure, l'ANSSI recommande des mots de passe bien plus longs (20+
caractères) pour rester résistant au brute-force en ligne.

État en mémoire, par processus : suffisant tant que core_api tourne en un
seul worker uvicorn (voir apps/core_api/Dockerfile, pas de --workers) — ne
survit pas à un redémarrage ni ne se partage entre plusieurs instances.
Passer par Redis (déjà dans la stack) serait l'étape suivante si le
service doit un jour tourner en plusieurs instances.
"""

import time
from collections import defaultdict

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60

_failed_attempts: dict[str, list[float]] = defaultdict(list)


def _recent_attempts(email: str) -> list[float]:
    now = time.time()
    attempts = [t for t in _failed_attempts[email] if now - t < LOCKOUT_SECONDS]
    _failed_attempts[email] = attempts
    return attempts


def is_locked_out(email: str) -> bool:
    return len(_recent_attempts(email)) >= MAX_ATTEMPTS


def record_failed_attempt(email: str) -> None:
    _recent_attempts(email).append(time.time())


def reset_attempts(email: str) -> None:
    _failed_attempts.pop(email, None)
