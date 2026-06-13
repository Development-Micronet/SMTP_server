import re
from collections import defaultdict
from datetime import datetime
from email.utils import parseaddr
from django.conf import settings
from django.contrib import messages as flash
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from mail.imap import ImapUnavailable, open_mailbox
from mail.models import MessageMeta
from mail.smtp import build_message, send


def _mailbox_or_404(request):
    mb = request.user.mailboxes.filter(active=True).first()
    if mb is None:
        from accounts.models import Mailbox
        # Fallback 1: If username contains '@', look up mailbox by exact address
        if "@" in request.user.username:
            local, dom = request.user.username.rsplit("@", 1)
            mb = Mailbox.objects.filter(local_part=local.lower().strip(), domain__name=dom.lower().strip(), active=True).first()
        
        # Fallback 1.5: If user's email field contains '@', look up mailbox by exact address
        if mb is None and getattr(request.user, "email", None) and "@" in request.user.email:
            local, dom = request.user.email.rsplit("@", 1)
            mb = Mailbox.objects.filter(local_part=local.lower().strip(), domain__name=dom.lower().strip(), active=True).first()
        
        # Fallback 2: Look up mailbox where local_part matches the username (e.g. 'admin' matches 'admin@polynexus.in')
        if mb is None:
            mb = Mailbox.objects.filter(local_part=request.user.username.lower().strip(), active=True).first()
            
    if mb is None:
        if request.user.is_staff:
            return None
        raise Http404("No mailbox is attached to this account.")
    return mb


class ThreadInfo:
    def __init__(self, latest_meta, count, senders_display, is_unread):
        self.meta = latest_meta
        self.thread_count = count
        self.senders_display = senders_display
        self.is_unread = is_unread
        
    @property
    def id(self):
        return self.meta.id
        
    @property
    def uid(self):
        return self.meta.uid
        
    @property
    def subject(self):
        return self.meta.subject
        
    @property
    def date(self):
        return self.meta.date
        
    @property
    def snippet(self):
        return self.meta.snippet
        
    @property
    def from_addr(self):
        return self.senders_display
        
    @property
    def seen(self):
        return not self.is_unread


@login_required
def inbox(request, folder: str = "INBOX"):
    from django.db.models import Count
    mb = _mailbox_or_404(request)
    if mb is None:
        return redirect("admin_panel:email_list")

    # Sync new mail from Dovecot on inbox load / refresh
    from mail.tasks import index_mailbox
    try:
        index_mailbox.run(None, mb.id, folder)
    except Exception:
        pass

    # Fetch latest 500 messages to group by conversation thread
    metas = list(MessageMeta.objects.filter(mailbox=mb, folder=folder).order_by('-date')[:500])
    
    # Group by conversation_id (maintaining order of newest message)
    conversation_groups = defaultdict(list)
    conv_order = []
    for m in metas:
        c_id = m.conversation_id
        if c_id not in conversation_groups:
            conv_order.append(c_id)
        conversation_groups[c_id].append(m)
        
    # Batch query the thread counts across all folders (to know total size of thread)
    counts = {
        r['conversation_id']: r['count']
        for r in MessageMeta.objects.filter(mailbox=mb, conversation_id__in=conv_order)
                                    .values('conversation_id')
                                    .annotate(count=Count('id'))
    }
    
    # Batch query all participants for these threads in chronological order
    all_thread_metas = list(MessageMeta.objects.filter(
        mailbox=mb, conversation_id__in=conv_order
    ).order_by('date'))
    
    # Group senders by conversation_id
    senders_map = defaultdict(list)
    for tm in all_thread_metas:
        c_id = tm.conversation_id
        from_addr = tm.from_addr
        name, addr = parseaddr(from_addr)
        sender_name = name if name else (addr.split('@')[0] if '@' in addr else addr)
        addr_lower = addr.lower()
        mb_addr_lower = mb.address.lower()
        mb_local_lower = mb.address.split('@')[0].lower()
        if addr_lower == mb_addr_lower or sender_name.lower() == mb_local_lower:
            sender_name = "me"
        if sender_name not in senders_map[c_id]:
            senders_map[c_id].append(sender_name)
            
    # Check if there is any unread message in the thread
    unread_map = defaultdict(bool)
    for tm in all_thread_metas:
        if not tm.seen:
            unread_map[tm.conversation_id] = True
            
    unique_threads = []
    for c_id in conv_order:
        group = conversation_groups[c_id]
        latest_meta = group[0] # The latest meta in the current folder
        
        # Compile senders display (e.g. "nisha, me" or just "nisha")
        sender_list = senders_map[c_id]
        senders_display = ", ".join(sender_list) if sender_list else latest_meta.from_addr
        
        thread_count = counts.get(c_id, len(group))
        is_unread = unread_map[c_id]
        
        unique_threads.append(ThreadInfo(latest_meta, thread_count, senders_display, is_unread))

    page = Paginator(unique_threads, 50).get_page(request.GET.get("page"))
    return render(request, "webmail/inbox.html",
                  {"mailbox": mb, "folder": folder, "page": page})


def _clean_subject(subject_str):
    if not subject_str:
        return ""
    return re.sub(r'^(?i)\s*(?:re|fwd|fw|aw)\s*:\s*', '', subject_str).strip()


@login_required
def message_detail(request, folder: str, uid: int):
    mb = _mailbox_or_404(request)
    if mb is None:
        return redirect("admin_panel:email_list")
        
    # 1. Find the target message metadata in DB
    target_meta = MessageMeta.objects.filter(mailbox=mb, folder=folder, uid=uid).first()
    if target_meta is None:
        # Fallback: if it's not indexed yet, index it first
        from mail.tasks import index_mailbox
        try:
            index_mailbox.run(None, mb.id, folder)
        except Exception:
            pass
        target_meta = MessageMeta.objects.filter(mailbox=mb, folder=folder, uid=uid).first()
        
    if target_meta is None:
        raise Http404("Message not found in database metadata.")
        
    # 2. Find all messages in the same conversation thread (by conversation_id)
    thread_metas = list(MessageMeta.objects.filter(
        mailbox=mb, 
        conversation_id=target_meta.conversation_id
    ).order_by('date'))
    
    # 3. Group thread metas by folder to batch fetch from IMAP
    folder_groups = defaultdict(list)
    for tm in thread_metas:
        folder_groups[tm.folder].append(tm.uid)
        
    # 4. Fetch the messages from IMAP
    fetched_messages = {}
    try:
        for fld, uids in folder_groups.items():
            with open_mailbox(mb.address, fld) as imap:
                # Mark only the target message as seen on IMAP server
                if fld == folder and uid in uids:
                    # Fetch target message with mark_seen=True
                    target_msgs = list(imap.fetch(f"UID {uid}", mark_seen=True))
                    if target_msgs:
                        fetched_messages[(fld, uid)] = target_msgs[0]
                    # Fetch other messages in the same folder with mark_seen=False
                    other_uids = [u for u in uids if u != uid]
                    if other_uids:
                        uids_str = ",".join(str(u) for u in other_uids)
                        for m in imap.fetch(f"UID {uids_str}", mark_seen=False):
                            fetched_messages[(fld, int(m.uid))] = m
                else:
                    # Fetch all messages in this folder with mark_seen=False
                    uids_str = ",".join(str(u) for u in uids)
                    for m in imap.fetch(f"UID {uids_str}", mark_seen=False):
                        fetched_messages[(fld, int(m.uid))] = m
    except ImapUnavailable:
        flash.error(request, "Mail server is unreachable right now.")
        return redirect("inbox")
        
    # 5. Assemble thread data for template
    messages_in_thread = []
    for tm in thread_metas:
        imap_msg = fetched_messages.get((tm.folder, tm.uid))
        if imap_msg:
            from_header = imap_msg.from_
            name, addr = parseaddr(from_header)
            sender_name = name if name else (addr.split('@')[0] if '@' in addr else addr)
            addr_lower = addr.lower()
            mb_addr_lower = mb.address.lower()
            mb_local_lower = mb.address.split('@')[0].lower()
            if addr_lower == mb_addr_lower or sender_name.lower() == mb_local_lower:
                sender_name = "me"
            sender_initial = sender_name[0].upper() if sender_name else "M"
            
            to_list = imap_msg.to
            formatted_to = []
            for t in to_list:
                t_name, t_addr = parseaddr(t)
                formatted_to.append(t_name if t_name else t_addr)
                
            messages_in_thread.append({
                "meta": tm,
                "imap": imap_msg,
                "body": imap_msg.text or "(no plain-text body)",
                "is_target": (tm.folder == folder and tm.uid == uid),
                "sender_name": sender_name,
                "sender_email": addr,
                "sender_initial": sender_initial,
                "formatted_to": ", ".join(formatted_to),
            })
            
    # Update target message seen state locally in DB
    MessageMeta.objects.filter(mailbox=mb, folder=folder, uid=uid).update(seen=True)
    
    # Prepare details of the last message in thread (for pre-filling quick reply details)
    last_msg = messages_in_thread[-1] if messages_in_thread else None
    cleaned = _clean_subject(target_meta.subject)
    
    return render(request, "webmail/message.html", {
        "mailbox": mb,
        "folder": folder,
        "target_uid": uid,
        "cleaned_subject": cleaned,
        "messages_in_thread": messages_in_thread,
        "last_msg": last_msg,
    })


@login_required
@require_POST
def message_delete(request, folder: str, uid: int):
    mb = _mailbox_or_404(request)
    if mb is None:
        return redirect("admin_panel:email_list")
    with open_mailbox(mb.address, folder) as imap:
        imap.delete([str(uid)])
    MessageMeta.objects.filter(mailbox=mb, folder=folder, uid=uid).delete()
    flash.success(request, "Message deleted.")
    return redirect("inbox")


@login_required
def compose(request):
    mb = _mailbox_or_404(request)
    if mb is None:
        flash.info(request, "Please create a mailbox first to send emails.")
        return redirect("admin_panel:mailbox_list")
    if request.method == "POST":
        to = [a.strip() for a in request.POST.get("to", "").split(",") if a.strip()]
        if not to:
            return HttpResponseBadRequest("Recipient required")
        attachments = []
        for f in request.FILES.getlist("attachments"):
            if f.size > settings.MAX_ATTACHMENT_BYTES:
                flash.error(request, f"{f.name} exceeds the attachment size limit.")
                return redirect("compose")
            attachments.append((f.name, f.read(), f.content_type or "application/octet-stream"))
            
        in_reply_to = request.POST.get("in_reply_to", "").strip()
        references = request.POST.get("references", "").strip()
        
        if in_reply_to and not references:
            parent = MessageMeta.objects.filter(mailbox=mb, message_id=in_reply_to).first()
            if parent:
                siblings = MessageMeta.objects.filter(mailbox=mb, conversation_id=parent.conversation_id).order_by('date')
                msg_ids = [s.message_id for s in siblings if s.message_id]
                unique_ids = []
                for mid in msg_ids:
                    if mid not in unique_ids:
                        unique_ids.append(mid)
                references = " ".join(unique_ids)

        msg = build_message(
            from_addr=mb.address, to=to,
            subject=request.POST.get("subject", ""),
            body=request.POST.get("body", ""),
            attachments=attachments,
            in_reply_to=in_reply_to,
            references=references,
        )
        send(msg)
        
        # Save a copy to the Sent folder on the IMAP server and trigger index
        try:
            with open_mailbox(mb.address, "INBOX") as imap:
                if not imap.folder.exists("Sent"):
                    imap.folder.create("Sent")
            with open_mailbox(mb.address, "Sent") as imap:
                imap.append(msg.as_bytes(), "Sent")
            
            # Sync the Sent folder immediately in the database
            from mail.tasks import index_mailbox
            index_mailbox.run(None, mb.id, "Sent")
        except Exception:
            pass

        flash.success(request, "Message sent.")
        return redirect("inbox")
    return render(request, "webmail/compose.html", {
        "mailbox": mb,
        "to": request.GET.get("to", ""),
        "subject": request.GET.get("subject", ""),
        "in_reply_to": request.GET.get("in_reply_to", ""),
    })


@login_required
def search(request):
    mb = _mailbox_or_404(request)
    if mb is None:
        return redirect("admin_panel:email_list")
    q = request.GET.get("q", "").strip()
    results = MessageMeta.objects.none()
    if q:
        results = MessageMeta.objects.filter(
            mailbox=mb, search_vector=SearchQuery(q)
        )[:100]
    return render(request, "webmail/search.html", {"mailbox": mb, "q": q, "results": results})
