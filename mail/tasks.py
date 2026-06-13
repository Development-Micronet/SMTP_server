"""Celery tasks: incremental IMAP -> Postgres indexing for listing & search."""
import logging

from celery import shared_task
from django.contrib.postgres.search import SearchVector
from django.db.models import Max

from accounts.models import Mailbox
from mail.imap import ImapUnavailable, open_mailbox
from mail.models import MessageMeta

log = logging.getLogger(__name__)


@shared_task
def index_all_mailboxes():
    for mb_id in Mailbox.objects.filter(active=True).values_list("id", flat=True):
        index_mailbox.delay(mb_id)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def index_mailbox(self, mailbox_id: int, folder: str = "INBOX"):
    import re
    import uuid
    mb = Mailbox.objects.get(pk=mailbox_id)
    last_uid = (
        MessageMeta.objects.filter(mailbox=mb, folder=folder)
        .aggregate(Max("uid"))["uid__max"] or 0
    )
    try:
        with open_mailbox(mb.address, folder) as imap:
            criteria = f"UID {last_uid + 1}:*"
            for m in imap.fetch(criteria, headers_only=True, mark_seen=False):
                uid = int(m.uid)
                if uid <= last_uid:  # IMAP returns the last message for n:* even if none are new
                    continue
                
                message_id = (m.headers.get("message-id", ("",))[0])[:998].strip()
                in_reply_to = (m.headers.get("in-reply-to", ("",))[0])[:998].strip()
                references_str = m.headers.get("references", ("",))[0]
                
                # Look up if this message already exists in database with conversation_id
                existing = MessageMeta.objects.filter(mailbox=mb, folder=folder, uid=uid).first()
                if existing and existing.conversation_id:
                    conversation_id = existing.conversation_id
                else:
                    conversation_id = ""
                    # 1. Try In-Reply-To
                    if in_reply_to:
                        parent = MessageMeta.objects.filter(mailbox=mb, message_id=in_reply_to).first()
                        if parent:
                            conversation_id = parent.conversation_id
                            
                    # 2. Try References list
                    if not conversation_id and references_str:
                        ref_ids = re.findall(r'<[^>]+>', references_str)
                        if ref_ids:
                            parent = MessageMeta.objects.filter(mailbox=mb, message_id__in=ref_ids).first()
                            if parent:
                                conversation_id = parent.conversation_id
                                
                    # 3. Fallback: subject-based sibling match
                    if not conversation_id:
                        subj_clean = (m.subject or "").strip()
                        while True:
                            match = re.match(r'^(?:re|fwd|fw|aw)\s*:\s*', subj_clean, re.IGNORECASE)
                            if not match:
                                break
                            subj_clean = subj_clean[match.end():].strip()
                        if subj_clean:
                            sibling = MessageMeta.objects.filter(mailbox=mb, subject__icontains=subj_clean).first()
                            if sibling:
                                conversation_id = sibling.conversation_id
                                
                    # 4. Generate new conversation UUID
                    if not conversation_id:
                        conversation_id = str(uuid.uuid4())
                
                MessageMeta.objects.update_or_create(
                    mailbox=mb, folder=folder, uid=uid,
                    defaults=dict(
                        message_id=message_id,
                        in_reply_to=in_reply_to,
                        conversation_id=conversation_id,
                        subject=m.subject or "",
                        from_addr=m.from_ or "",
                        to_addrs=", ".join(m.to),
                        date=m.date,
                        size=m.size or 0,
                        seen="\\Seen" in m.flags,
                        flagged="\\Flagged" in m.flags,
                        snippet=(m.text or "")[:280],
                    ),
                )
    except ImapUnavailable as exc:
        raise self.retry(exc=exc)

    MessageMeta.objects.filter(mailbox=mb, search_vector__isnull=True).update(
        search_vector=SearchVector("subject", "from_addr", "to_addrs", "snippet")
    )
    log.info("indexed mailbox=%s folder=%s", mb.address, folder)
