from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("work", "0008_profile_active_connections_alter_profile_bio_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="message",
            name="read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]