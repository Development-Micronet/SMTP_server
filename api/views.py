from django.http import Http404
from rest_framework import generics, views
from rest_framework.response import Response

from mail.imap import list_folders, open_mailbox
from mail.models import MessageMeta
from mail.smtp import build_message, send

from .serializers import MessageMetaSerializer, SendSerializer


def _mailbox(request):
    mb = request.user.mailboxes.filter(active=True).first()
    if mb is None:
        raise Http404("No mailbox for this account")
    return mb


class FolderListView(views.APIView):
    def get(self, request):
        return Response({"folders": list_folders(_mailbox(request).address)})


class MessageListView(generics.ListAPIView):
    serializer_class = MessageMetaSerializer

    def get_queryset(self):
        folder = self.request.query_params.get("folder", "INBOX")
        return MessageMeta.objects.filter(mailbox=_mailbox(self.request), folder=folder)


class MessageDetailView(views.APIView):
    def get(self, request, folder: str, uid: int):
        mb = _mailbox(request)
        with open_mailbox(mb.address, folder) as imap:
            msg = next(iter(imap.fetch(f"UID {uid}", mark_seen=False)), None)
        if msg is None or int(msg.uid) != uid:
            raise Http404
        return Response({
            "uid": uid, "subject": msg.subject, "from": msg.from_,
            "to": msg.to, "date": msg.date.isoformat() if msg.date else None,
            "text": msg.text,
            "attachments": [{"filename": a.filename, "size": a.size,
                             "content_type": a.content_type} for a in msg.attachments],
        })


class SendView(views.APIView):
    def post(self, request):
        mb = _mailbox(request)
        s = SendSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        msg = build_message(from_addr=mb.address, **s.validated_data)
        send(msg)
        return Response({"status": "queued", "message_id": msg["Message-ID"]}, status=202)
