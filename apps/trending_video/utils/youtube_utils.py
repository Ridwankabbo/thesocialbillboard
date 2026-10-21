from googleapiclient.discovery import build
from django.conf import settings

def get_trending_channel_ids(region_code='US', max_results=50):
    youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)

    trending_response = youtube.videos().list(
        part='snippet',
        chart='mostPopular',
        regionCode=region_code,
        maxResults=max_results
    ).execute()

    channel_ids = list({item['snippet']['channelId'] for item in trending_response['items']})
    return channel_ids


def get_channels_data_from_ids(channel_ids):
    youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)

    channels_data = []

    for i in range(0, len(channel_ids), 50):
        chunk = channel_ids[i:i+50]

        response = youtube.channels().list(
            part='snippet,statistics,brandingSettings',
            id=','.join(chunk)
        ).execute()

        for item in response['items']:
            branding = item.get('brandingSettings', {}).get('image', {})
            cover = branding.get('bannerExternalUrl', '')

            data = {
                'id': item['id'],
                'name': item['snippet']['title'],
                'description': item['snippet'].get('description', ''),
                'thumbnail': item['snippet']['thumbnails']['high']['url'],
                'cover_photo': cover,
                'channel_url': f"https://www.youtube.com/channel/{item['id']}",
                'subscribers': int(item['statistics'].get('subscriberCount', 0)),
                'videoCount': int(item['statistics'].get('videoCount', 0)),
            }

            channels_data.append(data)

    return channels_data


def infer_category(description):
    desc = description.lower()
    if 'game' in desc:
        return 'Gaming'
    elif 'vlog' in desc or 'daily life' in desc:
        return 'Lifestyle'
    elif 'comedy' in desc or 'funny' in desc:
        return 'Comedy'
    elif 'tech' in desc or 'review' in desc:
        return 'Tech'
    elif 'music' in desc:
        return 'Music'
    elif 'educat' in desc:
        return 'Education'
    else:
        return 'General'
