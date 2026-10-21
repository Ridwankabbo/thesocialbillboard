from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parents", "0011_parentplaylistprompt"),
    ]

    operations = [
        migrations.AddField(
            model_name="childprofile",
            name="name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="playlist",
            name="last_viewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
