from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("parents", "0007_playlist_link"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChildProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("age_band", models.CharField(choices=[("3-5", "Early Years (3-5)"), ("6-8", "Primary (6-8)"), ("9-11", "Upper Primary (9-11)"), ("12-14", "Early Secondary (12-14)"), ("15-16", "Mid Secondary (15-16)"), ("17-18", "Older Teens (17-18)")], max_length=10)),
                ("language", models.CharField(max_length=50)),
                ("preferences", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("parent", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="child_profiles", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name="playlist",
            name="child_profile",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="playlists", to="parents.childprofile"),
        ),
        migrations.AddField(
            model_name="playlist",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="playlist",
            name="filters_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="playlist",
            name="is_saved",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="playlist",
            name="session_length",
            field=models.PositiveIntegerField(blank=True, help_text="Session length in minutes", null=True),
        ),
        migrations.AddField(
            model_name="playlist",
            name="status",
            field=models.CharField(choices=[("queued", "Queued"), ("generating", "Generating"), ("ready", "Ready"), ("failed", "Failed")], default="queued", max_length=20),
        ),
        migrations.CreateModel(
            name="JobRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("task_name", models.CharField(max_length=100)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("done", "Done"), ("failed", "Failed")], default="queued", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("error", models.TextField(blank=True)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="job_runs", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="PlaylistExplanation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("why_suitable_text", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("playlist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="explanations", to="parents.playlist")),
            ],
        ),
        migrations.CreateModel(
            name="PlaylistItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("youtube_video_id", models.CharField(max_length=50)),
                ("position", models.PositiveIntegerField()),
                ("title", models.CharField(max_length=255)),
                ("duration", models.PositiveIntegerField(help_text="Duration in seconds")),
                ("channel_id", models.CharField(max_length=100)),
                ("thumbnail_url", models.URLField()),
                ("video_url", models.URLField()),
                ("playlist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="parents.playlist")),
            ],
            options={"ordering": ["position"], "unique_together": {("playlist", "position")}},
        ),
        migrations.CreateModel(
            name="YouTubeVideoCache",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("video_id", models.CharField(max_length=50, unique=True)),
                ("channel_id", models.CharField(max_length=100)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("duration", models.PositiveIntegerField(help_text="Duration in seconds")),
                ("publish_date", models.DateTimeField(blank=True, null=True)),
                ("transcript_text", models.TextField(blank=True, null=True)),
                ("analysis_json", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
