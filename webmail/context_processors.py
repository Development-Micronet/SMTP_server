from accounts.models import Mailbox
from mail.models import MessageMeta

def mailbox_counters(request):
    if not request.user.is_authenticated:
        return {}

    # Find the active mailbox attached to the user (replicating views.py logic safely)
    mb = request.user.mailboxes.filter(active=True).first()
    if mb is None:
        # Fallback 1: If username contains '@', look up mailbox by exact address
        if "@" in request.user.username:
            local, dom = request.user.username.rsplit("@", 1)
            mb = Mailbox.objects.filter(local_part=local.lower().strip(), domain__name=dom.lower().strip(), active=True).first()
        
        # Fallback 1.5: If user's email field contains '@', look up mailbox by exact address
        if mb is None and getattr(request.user, "email", None) and "@" in request.user.email:
            local, dom = request.user.email.rsplit("@", 1)
            mb = Mailbox.objects.filter(local_part=local.lower().strip(), domain__name=dom.lower().strip(), active=True).first()
        
        # Fallback 2: Look up mailbox where local_part matches the username
        if mb is None:
            mb = Mailbox.objects.filter(local_part=request.user.username.lower().strip(), active=True).first()

    if mb is None:
        return {}

    # Query unread conversation/thread counts for primary folders
    unread_counts = {}
    for folder in ["INBOX", "Spam", "Notifications", "Social"]:
        unread_counts[folder] = MessageMeta.objects.filter(
            mailbox=mb, folder=folder, seen=False
        ).values("conversation_id").distinct().count()

    # Query total drafts count
    drafts_count = MessageMeta.objects.filter(mailbox=mb, folder="Drafts").count()

    return {
        "unread_counts": unread_counts,
        "drafts_count": drafts_count,
    }
