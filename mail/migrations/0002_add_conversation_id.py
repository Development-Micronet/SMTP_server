from django.db import migrations, models

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
    ]
