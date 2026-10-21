from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projects.settings')

app = Celery('projects')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery beat tasks
app.conf.beat_schedule = {
    'fetch-spotify-data-daily': {
        'task': 'apps.spotify.tasks.fetch_spotify_podcasts',
        'schedule': crontab(hour=1, minute=0),
        # 'schedule': 300.0,
    },
    'fetch-smartmatchai-data-daily': {
        'task': 'apps.trending_video.tasks.fetch_and_store_smart_matchai_youtube_data',
        'schedule': crontab(hour=1, minute=0),
        # 'schedule': 300.0,
    },
    'fetch-top-uk-creators': {
        'task': 'apps.trending_video.tasks.fetch_and_store_top_uk_creators',
        'schedule': crontab(hour=1, minute=0),
        # 'schedule': 300.0,
    },
    'fetch-safe-channels': {
        'task': 'apps.trending_video.tasks.fetch_and_store_safe_channels',
        'schedule': crontab(hour=1, minute=0),
        # 'schedule': 300.0,
    },
    'fetch-trending-channels': {
        'task': 'apps.trending_video.tasks.fetch_and_store_trending_channels',
        'schedule': crontab(hour=1, minute=0),
        # 'schedule': 300.0,
    },
    'fetch-creators-every-6-hours': {
        'task': 'apps.creators_explore.tasks.fetch_and_store_creators',
        'schedule': crontab(hour=1, minute=0),
        # 'schedule': 300.0,
    },
    'sync-all-creators-every-hour': {
        'task': 'apps.creator_dashboard.tasks.sync_all_creators_profiles',
        'schedule': crontab(minute=0), # Every hour
    },
    'fetch-competitors-daily': {
        'task': 'apps.your_competitor.tasks.fetch_all_users_competitors',
        'schedule': crontab(hour=1, minute=0),
        # 'schedule': 300.0,
    },
    # 'social-analysis-daily-light-scan': {
    #     'task': 'apps.social_analysis.tasks.daily_light_scan',
    #     'schedule': crontab(hour=2, minute=0),
    # },
    # 'social-analysis-weekly-deep-scan': {
    #     'task': 'apps.social_analysis.tasks.weekly_deep_scan',
    #     'schedule': crontab(day_of_week="sun", hour=3, minute=0),
    # },
    
}
