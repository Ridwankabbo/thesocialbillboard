import requests
from celery import shared_task
from django.utils import timezone
from .models import ThirdPartyData
from dotenv import load_dotenv
import os

load_dotenv()
RAPIDAPI_KEY = config("RAPIDAPI_KEY")

RAPID_API_URL = "https://tiktok-api23.p.rapidapi.com/api/search/video"
HEADERS = {
    # "x-rapidapi-key": "f0ca56a7damsh5dc89a5f8c9cfd0p1ffb9fjsn0a330c6dad0a",
    "x-rapidapi-key": RAPIDAPI_KEY,

    "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
}

@shared_task
def fetch_tiktok_data():
    try:
        params = {"keyword": "cat", "cursor": "0", "search_id": "0"}
        response = requests.get(RAPID_API_URL, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        # print(data)

        ThirdPartyData.objects.update_or_create(
            name="tiktok_cat_videos",
            defaults={"data": data, "fetched_at": timezone.now()}
        )

        print("TikTok data updated successfully!")
    except Exception as e:
        print(f"Error fetching TikTok data: {e}")
