"""Politique de mot de passe (voir ANSSI-PG-078, "Recommandations relatives
à l'authentification multifacteur et aux mots de passe", 10/2021).

Priorité à la longueur plutôt qu'à la complexité de classes de caractères
(recommandation ANSSI la plus récente) : pas d'obligation de
majuscule/chiffre/caractère spécial, mais une longueur minimale plus
élevée, et un rejet des mots de passe triviaux ou prévisibles.
"""

import re

MIN_LENGTH = 12

_COMMON_PASSWORDS = {
    "password",
    "password123",
    "123456",
    "123456789",
    "12345678",
    "azerty",
    "azerty123",
    "qwerty",
    "qwerty123",
    "motdepasse",
    "changeme",
    "changeme1234",
    "admin",
    "administrator",
    "letmein",
    "letmein123",
    "welcome",
    "welcome123",
    "iloveyou",
    "monkey123",
    "dragon123",
    "master123",
    "sunshine123",
    "princess123",
    "football123",
    "baseball123",
}

_SEQUENTIAL_PATTERN = re.compile(
    r"(0123|1234|2345|3456|4567|5678|6789|abcd|bcde|cdef|defg|qwer|wert|erty|"
    r"azer|zert|erty|uiop)",
    re.IGNORECASE,
)


class WeakPasswordError(ValueError):
    """Le mot de passe ne respecte pas la politique minimale."""


def validate_password_strength(password: str, email: str | None = None) -> None:
    """Lève WeakPasswordError si le mot de passe est trop faible.

    Ne vérifie pas la présence de majuscules/chiffres/caractères spéciaux :
    l'ANSSI recommande désormais la longueur plutôt que la complexité de
    classes de caractères pour un mot de passe mémorisé par un humain.
    """
    if len(password) < MIN_LENGTH:
        raise WeakPasswordError(
            f"Le mot de passe doit contenir au moins {MIN_LENGTH} caractères."
        )

    if password.lower() in _COMMON_PASSWORDS:
        raise WeakPasswordError("Ce mot de passe est trop courant.")

    if len(set(password)) == 1:
        raise WeakPasswordError("Le mot de passe ne doit pas être un seul caractère répété.")

    if _SEQUENTIAL_PATTERN.search(password):
        raise WeakPasswordError(
            "Le mot de passe ne doit pas contenir de séquence évidente (ex: 1234, azer)."
        )

    if email:
        local_part = email.split("@", 1)[0].lower()
        if len(local_part) >= 3 and local_part in password.lower():
            raise WeakPasswordError("Le mot de passe ne doit pas contenir votre identifiant.")
