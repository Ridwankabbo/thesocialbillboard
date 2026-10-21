from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parents", "0008_parents_dashboard_v1"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParentPlaylistPrompt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prompt_text", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]

