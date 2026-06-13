import pytest
from django.contrib.auth import get_user_model

from accounts.models import Domain, Mailbox
from accounts.services import dovecot_hash


@pytest.fixture
def mailbox(db):
    user = get_user_model().objects.create_user("alice@example.com", password="x" * 12)
    domain = Domain.objects.create(name="example.com")
    return Mailbox.objects.create(
        user=user, domain=domain, local_part="alice",
        password_hash=dovecot_hash("correct horse battery staple"),
    )
