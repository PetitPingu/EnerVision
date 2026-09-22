import pytest
from infrastructure.password_policy import WeakPasswordError, validate_password_strength


def test_accepts_a_long_enough_unpredictable_password():
    validate_password_strength("correct-horse-battery")


def test_rejects_password_shorter_than_minimum_length():
    with pytest.raises(WeakPasswordError):
        validate_password_strength("short1234")


def test_rejects_a_common_password():
    with pytest.raises(WeakPasswordError):
        validate_password_strength("password123")


def test_rejects_a_single_repeated_character():
    with pytest.raises(WeakPasswordError):
        validate_password_strength("aaaaaaaaaaaa")


def test_rejects_an_obvious_sequence():
    with pytest.raises(WeakPasswordError):
        validate_password_strength("my-pass-1234-word")


def test_rejects_password_containing_the_account_email_local_part():
    with pytest.raises(WeakPasswordError):
        validate_password_strength("alicealice999", email="alice@example.com")


def test_does_not_require_character_class_complexity():
    # Recommandation ANSSI la plus récente : la longueur prime sur la
    # complexité de classes de caractères (pas de majuscule/chiffre exigé).
    validate_password_strength("lowercaseonlyword")
