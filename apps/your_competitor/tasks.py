# apps/api_test/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from .views import extract_channel_id, get_channel_keywords, find_competitors
from .models import CompetitorData

User = get_user_model()

@shared_task
def fetch_all_users_competitors():
    users = User.objects.exclude(youtube_link__isnull=True).exclude(youtube_link="")

    for user in users:
        channel_id = extract_channel_id(user.youtube_link)
        if not channel_id:
            continue

        keywords, channel_name, subscriber_count = get_channel_keywords(channel_id)
        if not keywords:
            continue

        competitors = find_competitors(keywords)

        data_to_save = {
            "input_channel": {
                "name": channel_name,
                "channelId": channel_id,
                "subscribers": subscriber_count,
                "url": f"https://www.youtube.com/channel/{channel_id}"
            },
            "competitors": competitors
        }

        CompetitorData.objects.update_or_create(
            user=user,
            defaults={
                "fetched_date": timezone.now(),
                "data": data_to_save
            }
        )

    return f"Competitor data updated for {users.count()} users"




@shared_task
def fetch_competitors_for_user_task(user_id):
    print("user_id", user_id)
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return "User not found"
    channel_id = extract_channel_id(user.youtube_link)
    if not channel_id:
        return "No valid channel_id"

    keywords, channel_name, subscriber_count = get_channel_keywords(channel_id)
    if not keywords:
        return "No keywords"

    competitors = find_competitors(keywords)
    data_to_save = {
        "input_channel": {
            "name": channel_name,
            "channelId": channel_id,
            "subscribers": subscriber_count,
            "url": f"https://www.youtube.com/channel/{channel_id}"
        },
        "competitors": competitors
    }

    CompetitorData.objects.update_or_create(
        user=user,
        defaults={
            "fetched_date": timezone.now(),
            "data": data_to_save
        }
    )
    return f"Competitors updated for {user.email}"
