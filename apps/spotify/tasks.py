# from celery import shared_task
# from django.utils import timezone
# from .models import SpotifyData
# import requests
# import base64
# import os

# CLIENT_ID = config("SPOTIFY_CLIENT_ID")
# CLIENT_SECRET = config("SPOTIFY_CLIENT_SECRET")

# def get_spotify_token():
#     auth_url = 'https://accounts.spotify.com/api/token'
#     auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
#     headers = {
#         'Authorization': f'Basic {auth_header}',
#         'Content-Type': 'application/x-www-form-urlencoded'
#     }
#     data = {'grant_type': 'client_credentials'}
#     response = requests.post(auth_url, headers=headers, data=data)
#     return response.json().get('access_token')


# @shared_task
# def fetch_spotify_podcasts():
#     token = get_spotify_token()
#     if not token:
#         return "Token fetch failed."

#     query = 'parenting'
#     limit = 10
#     url = f"https://api.spotify.com/v1/search?q={query}&type=show&market=US&limit={limit}"
#     headers = {'Authorization': f'Bearer {token}'}
#     response = requests.get(url, headers=headers)

#     if response.status_code != 200:
#         return f"Failed to fetch from Spotify. Status code: {response.status_code}"

#     shows = response.json().get('shows', {}).get('items', [])
#     if not shows:
#         return "No podcast data found."

#     SpotifyData.objects.update_or_create(
#         name="spotify_latest_parenting",  # fixed name for consistent overwrite
#         defaults={
#             "data": shows,
#             "fetched_at": timezone.now()
#         }
#     )

#     return f"{len(shows)} podcasts updated in DB."



# app/spotify/tasks.py
from celery import shared_task
from .services import fetch_and_store_spotify_podcasts

@shared_task
def fetch_spotify_podcasts():
    items = fetch_and_store_spotify_podcasts()
    if items is None:
        return "Failed to fetch from Spotify."
    return f"{len(items)} podcasts updated in DB."