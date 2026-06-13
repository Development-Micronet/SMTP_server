"""View tests with the IMAP/SMTP layers mocked out.

Full round-trip tests (send on 587, assert arrival via IMAP) live in CI
against the real docker compose stack — see .github/workflows/ci.yml.
"""
from unittest.mock import patch

import pytest
from django.urls import reverse

from mail.models import MessageMeta


@pytest.mark.django_db
def test_inbox_requires_login(client):
    assert client.get(reverse("inbox")).status_code == 302


@pytest.mark.django_db
def test_inbox_lists_indexed_messages(client, mailbox):
    MessageMeta.objects.create(mailbox=mailbox, uid=1, subject="Hello",
                               from_addr="bob@example.org")
    client.force_login(mailbox.user)
    resp = client.get(reverse("inbox"))
    assert resp.status_code == 200
    assert b"Hello" in resp.content


@pytest.mark.django_db
@patch("webmail.views.send")
def test_compose_sends(mock_send, client, mailbox):
    client.force_login(mailbox.user)
    resp = client.post(reverse("compose"), {
        "to": "bob@example.org", "subject": "Hi", "body": "Test"})
    assert resp.status_code == 302
    msg = mock_send.call_args[0][0]
    assert msg["From"] == "alice@example.com"
    assert msg["To"] == "bob@example.org"
