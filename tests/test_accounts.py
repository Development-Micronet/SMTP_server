import pytest

from accounts.services import dovecot_hash, generate_app_password, verify


def test_hash_roundtrip():
    h = dovecot_hash("s3cret-passphrase")
    assert h.startswith("{ARGON2ID}$argon2id$")
    assert verify("s3cret-passphrase", h)
    assert not verify("wrong", h)


def test_app_password_format():
    p = generate_app_password()
    assert len(p) == 19 and p.count("-") == 3


@pytest.mark.django_db
def test_mailbox_address_and_maildir(mailbox):
    assert mailbox.address == "alice@example.com"
    assert mailbox.maildir_path == "/var/vmail/example.com/alice/"
