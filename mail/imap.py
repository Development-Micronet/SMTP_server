"""Thin IMAP layer: the webmail/API never touch the Maildir on disk.

We log in with Dovecot's *master user* mechanism (user*masteruser + master
password), so Django needs exactly one service credential and no copy of
the user's own password. Enable it in compose/dovecot/conf.d/auth-master.
"""
from contextlib import contextmanager

from django.conf import settings
from imap_tools import MailBox, MailboxLoginError


class ImapUnavailable(Exception):
    pass


@contextmanager
def open_mailbox(address: str, folder: str = "INBOX"):
    login = f"{address}*{settings.DOVECOT_MASTER_USER}"
    try:
        with MailBox(settings.IMAP_HOST).login(
            login, settings.DOVECOT_MASTER_PASSWORD, initial_folder=folder
        ) as mb:
            yield mb
    except MailboxLoginError as exc:
        raise ImapUnavailable(f"IMAP login failed for {address}") from exc


def list_folders(address: str) -> list[str]:
    with open_mailbox(address) as mb:
        return [f.name for f in mb.folder.list()]
