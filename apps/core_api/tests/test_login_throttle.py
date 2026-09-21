from infrastructure.login_throttle import (
    MAX_ATTEMPTS,
    is_locked_out,
    record_failed_attempt,
    reset_attempts,
)


def test_not_locked_out_with_no_attempts():
    assert not is_locked_out("fresh@example.com")


def test_locks_out_after_max_attempts():
    email = "bruteforced@example.com"
    for _ in range(MAX_ATTEMPTS):
        assert not is_locked_out(email)
        record_failed_attempt(email)

    assert is_locked_out(email)


def test_reset_clears_the_lockout():
    email = "recovered@example.com"
    for _ in range(MAX_ATTEMPTS):
        record_failed_attempt(email)
    assert is_locked_out(email)

    reset_attempts(email)

    assert not is_locked_out(email)
