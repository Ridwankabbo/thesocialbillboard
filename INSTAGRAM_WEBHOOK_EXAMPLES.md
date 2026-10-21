# Instagram Webhook Integration - Usage Examples

## Table of Contents
1. [Authentication Flow](#authentication-flow)
2. [Webhook Configuration](#webhook-configuration)
3. [Processing Events](#processing-events)
4. [Querying Events](#querying-events)
5. [API Endpoints](#api-endpoints)
6. [Advanced Examples](#advanced-examples)

---

## Authentication Flow

### Step 1: User Gets Instagram Auth URL

**Endpoint**: `POST /v1/plartform/instragram/auth/`

```python
import requests

response = requests.post(
    'http://your-domain.com/v1/plartform/instragram/auth/',
    headers={'Authorization': f'Bearer {user_token}'}
)

auth_url = response.json()['data']
# Redirect user to this URL
```

### Step 2: User Authorizes and Returns

After user grants permissions, they're redirected to:

**Endpoint**: `/v1/plartform/instragram/callback/?code=...&state=...`

This is automatic. The callback handler will:
- Exchange authorization code for access token
- Convert short-lived token to long-lived token
- Get Facebook page and Instagram business account ID
- Save credentials to database
- **Store Instagram account ID in `profile.meta['instagram']['ig_account_id']`** ← This is crucial for webhooks!

---

## Webhook Configuration

### Get Webhook Info

**Endpoint**: `GET /v1/plartform/instragram/webhook/info/`

```python
import requests

response = requests.get(
    'http://your-domain.com/v1/plartform/instragram/webhook/info/',
    headers={'Authorization': f'Bearer {user_token}'}
)

info = response.json()['data']
# {
#   "webhook_url": "https://your-domain.com/v1/plartfrom/instagram/webhook/",
#   "verify_token": "your_custom_verify_token",
#   "instructions": "Configure this webhook URL..."
# }
```

### Subscribe Instagram Account to Webhooks

After user authenticates, subscribe their Instagram account:

```python
import requests
from apps.creator_dashboard.models import CreatorProfile, CreatroCredentials

# Get user's Instagram credentials
profile = CreatorProfile.objects.get(user=user)
creds = CreatroCredentials.objects.get(
    profile=profile,
    plartform="INSTAGRAM"
)

# Get page ID from profile meta
page_id = profile.meta['instagram']['page_id']
access_token = creds.access_token

# Subscribe to webhooks
response = requests.post(
    f"https://graph.facebook.com/v19.0/{page_id}/subscribed_apps",
    params={"access_token": access_token}
)

print(response.json())
# Expected: {"success": true}
```

---

## Processing Events

### How Webhook Events Flow

When a user takes action on Instagram (likes, comments, posts), Instagram sends:

```json
POST /v1/plartfrom/instagram/webhook/

{
  "entry": [
    {
      "id": "1234567890",  # Instagram business account ID
      "changes": [
        {
          "value": {
            "media_id": "17999999999999999",
            "caption": "Amazing photo!",
            "like_count": 42,
            "comments_count": 5,
            "timestamp": "2024-01-01T10:30:00+0000",
            "comment_text": "Love this!",
            "commenter_id": "9876543210"
          },
          "field": "media"
        }
      ]
    }
  ]
}
```

The webhook endpoint will:
1. Extract IG account ID from `entry[0]['id']`
2. Find the CreatorProfile where `meta['instagram']['ig_account_id']` matches
3. Call `process_instagram_webhook_event(webhook_data, profile)`
4. Save event to `InstagramWebhookEvent` model
5. Update `ProfileVideos` with latest stats

---

## Querying Events

### Basic Queries

```python
from apps.creator_dashboard.models import InstagramWebhookEvent, CreatorProfile

# Get user's profile
profile = CreatorProfile.objects.get(user=user)

# Get all events
all_events = InstagramWebhookEvent.objects.filter(profile=profile).order_by('-timestamp')

# Get events from last 7 days
from datetime import timedelta
from django.utils import timezone

week_ago = timezone.now() - timedelta(days=7)
recent_events = InstagramWebhookEvent.objects.filter(
    profile=profile,
    timestamp__gte=week_ago
).order_by('-timestamp')

# Get only like events
likes = InstagramWebhookEvent.objects.filter(
    profile=profile,
    event_type='like'
)

# Get only comments with text
comments = InstagramWebhookEvent.objects.filter(
    profile=profile,
    event_type='comment'
).exclude(comment_text__isnull=True)

# Get specific media's events
media_events = InstagramWebhookEvent.objects.filter(
    profile=profile,
    media_id='17999999999999999'
)
```

### Statistics & Aggregation

```python
from django.db.models import Count, Sum, Avg

# Count events by type
event_counts = InstagramWebhookEvent.objects.filter(
    profile=profile
).values('event_type').annotate(
    count=Count('id')
)

# Example output:
# [
#   {'event_type': 'like', 'count': 42},
#   {'event_type': 'comment', 'count': 15},
#   {'event_type': 'post', 'count': 5}
# ]

# Total engagement
total_likes = InstagramWebhookEvent.objects.filter(
    profile=profile
).aggregate(total=Sum('like_count'))['total']

total_comments = InstagramWebhookEvent.objects.filter(
    profile=profile
).aggregate(total=Sum('comment_count'))['total']

# Average engagement per event
avg_stats = InstagramWebhookEvent.objects.filter(
    profile=profile,
    event_type='post'
).aggregate(
    avg_likes=Avg('like_count'),
    avg_comments=Avg('comment_count')
)

# Group by date
from django.db.models.functions import TruncDate

daily_events = InstagramWebhookEvent.objects.filter(
    profile=profile
).annotate(
    event_date=TruncDate('timestamp')
).values('event_date').annotate(
    count=Count('id')
).order_by('event_date')
```

---

## API Endpoints

### Example: Get User's Webhook Events

Create this view:

```python
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.creator_dashboard.models import CreatorProfile, InstagramWebhookEvent
from apps.creator_dashboard.serializers import InstagramWebhookEventSerializer

class UserInstagramWebhookEventsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's Instagram webhook events"""
        profile = CreatorProfile.objects.get(user=request.user)
        
        # Get query parameters
        event_type = request.query_params.get('event_type')  # Filter by event type
        limit = int(request.query_params.get('limit', 50))    # Default 50 events
        
        # Build query
        events = InstagramWebhookEvent.objects.filter(profile=profile)
        
        if event_type:
            events = events.filter(event_type=event_type)
        
        events = events.order_by('-timestamp')[:limit]
        
        # Serialize
        serializer = InstagramWebhookEventSerializer(events, many=True)
        
        return Response({
            'count': events.count(),
            'events': serializer.data
        })


# Add to urls.py
path('v1/user/instagram/events/', UserInstagramWebhookEventsView.as_view(), name='user-instagram-events')
```

Usage:

```bash
# Get all events
GET /v1/user/instagram/events/
Authorization: Bearer {token}

# Get only comments
GET /v1/user/instagram/events/?event_type=comment

# Get last 20 likes
GET /v1/user/instagram/events/?event_type=like&limit=20
```

---

## Advanced Examples

### Example 1: Dashboard Stats View

```python
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Sum
from apps.creator_dashboard.models import CreatorProfile, InstagramWebhookEvent

class InstagramStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get Instagram engagement stats"""
        profile = CreatorProfile.objects.get(user=request.user)
        
        # Event counts
        event_counts = InstagramWebhookEvent.objects.filter(
            profile=profile
        ).values('event_type').annotate(count=Count('id'))
        
        # Total engagement
        total_stats = InstagramWebhookEvent.objects.filter(
            profile=profile
        ).aggregate(
            total_likes=Sum('like_count'),
            total_comments=Sum('comment_count'),
            total_views=Sum('view_count')
        )
        
        # Most commented media
        most_commented = InstagramWebhookEvent.objects.filter(
            profile=profile
        ).values('media_id').annotate(
            total_comments=Sum('comment_count')
        ).order_by('-total_comments').first()
        
        return Response({
            'events_by_type': event_counts,
            'total_engagement': total_stats,
            'most_commented_media': most_commented
        })
```

### Example 2: Real-time Notification View

```python
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.creator_dashboard.models import CreatorProfile, InstagramWebhookEvent
from django.utils import timezone
from datetime import timedelta

class RecentActivityView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get recent activity (last 24 hours)"""
        profile = CreatorProfile.objects.get(user=request.user)
        
        # Last 24 hours
        day_ago = timezone.now() - timedelta(days=1)
        
        recent_events = InstagramWebhookEvent.objects.filter(
            profile=profile,
            timestamp__gte=day_ago
        ).order_by('-timestamp')
        
        # Group by type
        grouped = {}
        for event in recent_events:
            event_type = event.get_event_display()
            if event_type not in grouped:
                grouped[event_type] = []
            
            grouped[event_type].append({
                'media_id': event.media_id,
                'timestamp': event.timestamp,
                'description': self._get_description(event)
            })
        
        return Response(grouped)
    
    def _get_description(self, event):
        if event.event_type == 'like':
            return f"Post received {event.like_count} new likes"
        elif event.event_type == 'comment':
            return f"New comment: {event.comment_text[:50]}"
        elif event.event_type == 'post':
            return f"New post: {event.caption[:50]}"
        elif event.event_type == 'view':
            return f"Post received {event.view_count} views"
        return str(event.event_type)
```

### Example 3: Export Events to CSV

```python
import csv
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.creator_dashboard.models import CreatorProfile, InstagramWebhookEvent

class ExportWebhookEventsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Export Instagram webhook events to CSV"""
        profile = CreatorProfile.objects.get(user=request.user)
        events = InstagramWebhookEvent.objects.filter(profile=profile)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="instagram_events.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date',
            'Event Type',
            'Media ID',
            'Likes',
            'Comments',
            'Views',
            'Caption',
            'Reaction Type'
        ])
        
        for event in events:
            writer.writerow([
                event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                event.get_event_display(),
                event.media_id,
                event.like_count,
                event.comment_count,
                event.view_count,
                event.caption or '',
                event.reaction_type or ''
            ])
        
        return response
```

---

## Testing

### Manual Webhook Test

```python
# Django shell
python manage.py shell

from apps.creator_dashboard.models import CreatorProfile, InstagramWebhookEvent
from apps.creator_dashboard.service import process_instagram_webhook_event

# Get a profile
profile = CreatorProfile.objects.first()

# Create test webhook data
test_webhook = {
    "entry": [{
        "id": profile.meta['instagram']['ig_account_id'],
        "changes": [{
            "value": {
                "media_id": "123456789",
                "caption": "Test post",
                "like_count": 10,
                "comments_count": 5,
                "view_count": 100,
                "timestamp": "2024-01-01T10:00:00+0000"
            }
        }]
    }]
}

# Process webhook
process_instagram_webhook_event(test_webhook, profile)

# Check if event was saved
event = InstagramWebhookEvent.objects.last()
print(event)
# Output: Test User - post - 123456789
```

---

## Troubleshooting

### Events Not Being Saved

1. **Check profile meta**
   ```python
   from apps.creator_dashboard.models import CreatorProfile
   profile = CreatorProfile.objects.get(user=user)
   print(profile.meta.get('instagram', {}))
   # Should have 'ig_account_id' key
   ```

2. **Check if profile is found**
   - Add debug print to webhook view
   - Verify webhook account ID matches stored ID

3. **Check permissions**
   - Verify Instagram app has correct permissions
   - Ensure access token is still valid

### Webhook URL Not Accessible

```bash
# Test publicly accessible
curl -X GET "https://your-domain.com/v1/plartfrom/instagram/webhook/?hub.mode=subscribe&hub.verify_token=test&hub.challenge=test123"

# Should return: test123
```

---

## Next Steps

1. ✅ Test webhook locally with ngrok
2. ✅ Deploy to production
3. ✅ Monitor webhook logs
4. ✅ Create dashboard for users to view their events
5. ✅ Set up real-time notifications
6. ✅ Build analytics reports

