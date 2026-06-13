"""Password hashing shared between Django and Dovecot.

Dovecot understands "{ARGON2ID}<argon2 encoded hash>" out of the box, and
Django's Argon2PasswordHasher produces "argon2$<encoded>". We store the
Dovecot-form hash on Mailbox so a single secret works for IMAP, SMTP
submission (SASL via Dovecot) and can be verified by Django too.
"""
import secrets

from argon2 import PasswordHasher

_ph = PasswordHasher()


def dovecot_hash(plaintext: str) -> str:
    return "{ARGON2ID}" + _ph.hash(plaintext)


def verify(plaintext: str, stored: str) -> bool:
    try:
        encoded = stored.removeprefix("{ARGON2ID}")
        return _ph.verify(encoded, plaintext)
    except Exception:
        return False


def generate_app_password() -> str:
    """16 lowercase chars in 4-char groups, like Google app passwords."""
    raw = secrets.token_hex(8)
    return "-".join(raw[i : i + 4] for i in range(0, 16, 4))
