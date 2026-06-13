from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('dkim_selector', models.CharField(default='mail', max_length=63)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Mailbox',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('local_part', models.CharField(max_length=64)),
                ('password_hash', models.CharField(max_length=512)),
                ('maildir_path', models.CharField(editable=False, max_length=512)),
                ('quota_mb', models.PositiveIntegerField(default=2048)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('domain', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.domain')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mailboxes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'mailboxes',
                'unique_together': {('domain', 'local_part')},
            },
        ),
        migrations.CreateModel(
            name='AppPassword',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=64)),
                ('password_hash', models.CharField(max_length=512)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_used_at', models.DateTimeField(blank=True, null=True)),
                ('mailbox', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='app_passwords', to='accounts.mailbox')),
            ],
        ),
        migrations.CreateModel(
            name='Alias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(blank=True, max_length=64)),
                ('destination', models.EmailField(max_length=254)),
                ('active', models.BooleanField(default=True)),
                ('domain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.domain')),
            ],
            options={
                'verbose_name_plural': 'aliases',
                'unique_together': {('domain', 'source', 'destination')},
            },
        ),
    ]
