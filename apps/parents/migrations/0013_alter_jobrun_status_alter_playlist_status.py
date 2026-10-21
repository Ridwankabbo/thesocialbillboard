from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parents", "0012_childprofile_name_playlist_last_viewed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jobrun",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("done", "Done"),
                    ("failed", "Failed"),
                    ("canceled", "Canceled"),
                ],
                default="queued",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="playlist",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("generating", "Generating"),
                    ("ready", "Ready"),
                    ("failed", "Failed"),
                    ("canceled", "Canceled"),
                ],
                default="queued",
                max_length=20,
            ),
        ),
    ]
