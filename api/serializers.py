from rest_framework import serializers

from mail.models import MessageMeta


class MessageMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageMeta
        fields = ["uid", "folder", "subject", "from_addr", "to_addrs",
                  "date", "size", "seen", "flagged", "snippet"]


class SendSerializer(serializers.Serializer):
    to = serializers.ListField(child=serializers.EmailField(), min_length=1)
    cc = serializers.ListField(child=serializers.EmailField(), required=False, default=list)
    subject = serializers.CharField(allow_blank=True, default="")
    body = serializers.CharField(allow_blank=True, default="")
