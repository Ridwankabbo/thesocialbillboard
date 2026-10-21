# app/spotify/services.py
import os
import base64
import requests
from django.utils import timezone
from .models import SpotifyData

CLIENT_ID = config("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = config("SPOTIFY_CLIENT_SECRET")

def _get_spotify_token():
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    r = requests.post(auth_url, headers=headers, data=data, timeout=15)
    r.raise_for_status()
    return r.json().get('access_token')

def fetch_and_store_spotify_podcasts(query='parenting podcast', limit=10, name='spotify_latest_parenting', market='US'):
    """
    Spotify API থেকে শোগুলো এনে SpotifyData টেবিলে আপডেট/ক্রিয়েট করে।
    সফল হলে items লিস্ট রিটার্ন করে; ব্যর্থ হলে None রিটার্ন করে।
    """
    token = _get_spotify_token()
    if not token:
        return None

    url = f"https://api.spotify.com/v1/search?q={query}&type=show&market={market}&limit={limit}"
    headers = {'Authorization': f'Bearer {token}'}

    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code != 200:
        return None

    items = r.json().get('shows', {}).get('items', [])
    if not items:
        return []

    # overwrite-by-name
    SpotifyData.objects.update_or_create(
        name=name,
        defaults={
            "data": items,
            "fetched_at": timezone.now()
        }
    )
    return items
