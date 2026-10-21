from celery import shared_task
from django.utils import timezone
from .models import Creator
from .views import fetch_trending_tiktok_users, fetch_trending_instagram_users, fetch_trending_youtube_channels

@shared_task
def fetch_and_store_creators():
    creators = []
    creators.extend(fetch_trending_tiktok_users())
    creators.extend(fetch_trending_youtube_channels())
    creators.extend(fetch_trending_instagram_users())

    for data in creators:
        Creator.objects.update_or_create(
            name=data["name"],
            platform=data["platform"],
            defaults={
                "followers": data["followers"],
                "image": data["image"],
                "genre": data["genre"],
                "country": data["country"],
                "age_group": data["age_group"],
                "channel_url": data["channel_url"],
                "fetched_at": timezone.now(),
            }
        )
    return f"{len(creators)} creators stored."
