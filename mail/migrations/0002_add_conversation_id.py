import re
import uuid
from django.db import migrations, models

def _clean_subject(subject_str):
    if not subject_str:
        return ""
    return re.sub(r'^(?i)\s*(?:re|fwd|fw|aw)\s*:\s*', '', subject_str).strip()

def backfill_conversation_ids(apps, schema_editor):
    MessageMeta = apps.get_model('mail', 'MessageMeta')
    
    # Process each mailbox separately
    for mb_id in MessageMeta.objects.values_list('mailbox_id', flat=True).distinct():
        # Get all messages for this mailbox ordered by date
        metas = list(MessageMeta.objects.filter(mailbox_id=mb_id).order_by('date'))
        
        # Group messages by cleaned subject
        subject_threads = {}
        for m in metas:
            subj_clean = _clean_subject(m.subject).lower()
            if subj_clean not in subject_threads:
                subject_threads[subj_clean] = str(uuid.uuid4())
            
            m.conversation_id = subject_threads[subj_clean]
            m.save()

class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='messagemeta',
            name='conversation_id',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name='messagemeta',
            name='in_reply_to',
            field=models.CharField(blank=True, db_index=True, max_length=998),
        ),
        migrations.RunPython(backfill_conversation_ids, reverse_code=migrations.RunPython.noop),
    ]
