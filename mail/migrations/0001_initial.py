import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageMeta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('folder', models.CharField(default='INBOX', max_length=255)),
                ('uid', models.PositiveIntegerField()),
                ('message_id', models.CharField(blank=True, db_index=True, max_length=998)),
                ('subject', models.TextField(blank=True)),
                ('from_addr', models.CharField(blank=True, max_length=998)),
                ('to_addrs', models.TextField(blank=True)),
                ('date', models.DateTimeField(db_index=True, null=True)),
                ('size', models.PositiveIntegerField(default=0)),
                ('seen', models.BooleanField(default=False)),
                ('flagged', models.BooleanField(default=False)),
                ('has_attachments', models.BooleanField(default=False)),
                ('snippet', models.CharField(blank=True, max_length=280)),
                ('search_vector', django.contrib.postgres.search.SearchVectorField(null=True)),
                ('indexed_at', models.DateTimeField(auto_now=True)),
                ('mailbox', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='accounts.mailbox')),
            ],
            options={
                'ordering': ['-date'],
                'indexes': [
                    django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='mail_messag_search__205b38_gin'),
                    models.Index(fields=['mailbox', 'folder', '-date'], name='mail_messag_mailbox_82e88a_idx'),
                ],
                'unique_together': {('mailbox', 'folder', 'uid')},
            },
        ),
    ]
