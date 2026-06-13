"""Message metadata mirror used for fast listing and full-text search.

The authoritative store is the Maildir owned by Dovecot; rows here are an
index built by mail.tasks and can always be rebuilt from IMAP.
"""
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models

from accounts.models import Mailbox


class MessageMeta(models.Model):
    mailbox = models.ForeignKey(Mailbox, on_delete=models.CASCADE, related_name="messages")
    folder = models.CharField(max_length=255, default="INBOX")
    uid = models.PositiveIntegerField()
    message_id = models.CharField(max_length=998, blank=True, db_index=True)
    subject = models.TextField(blank=True)
    from_addr = models.CharField(max_length=998, blank=True)
    to_addrs = models.TextField(blank=True)
    date = models.DateTimeField(null=True, db_index=True)
    size = models.PositiveIntegerField(default=0)
    seen = models.BooleanField(default=False)
    flagged = models.BooleanField(default=False)
    has_attachments = models.BooleanField(default=False)
    snippet = models.CharField(max_length=280, blank=True)
    search_vector = SearchVectorField(null=True)
    indexed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("mailbox", "folder", "uid")
        indexes = [
            GinIndex(fields=["search_vector"]),
            models.Index(fields=["mailbox", "folder", "-date"]),
        ]
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"[{self.mailbox.address}/{self.folder}#{self.uid}] {self.subject[:40]}"
