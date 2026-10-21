# Instagram Webhook Integration Setup Guide

## Overview
This document explains how to set up Instagram webhook integration to automatically save user actions (posts, likes, comments, views, shares) to your database using the newly implemented `InstagramWebhookEvent` model.

## Architecture

### Core Components
1. **Model**: `InstagramWebhookEvent` - Stores all Instagram webhook events
2. **Service**: `process_instagram_webhook_event()` - Processes and saves webhook data
3. **View**: `instagram_webhook()` - Webhook endpoint (GET for verification, POST for events)
4. **Admin**: Dashboard to view and filter webhook events

### Event Types Tracked
- **post** - New media published
- **like** - Post received likes/reactions
- **comment** - Post received comments
- **view** - Media received views (stories, reels)
- **share** - Media was shared

---

## Setup Instructions

### Step 1: Set Environment Variables

Add these to your `.env` file or `settings.py`:

```python
# Instagram OAuth Credentials
INSTAGRAM_CLIENT_ID = "your_client_id"
INSTAGRAM_CLIENT_SECRET = "your_client_secret"
INSTAGRAM_REDIRECT_URI = "http://your-domain.com/v1/plartform/instragram/callback/"
INSTAGRAM_VERIFY_TOKEN = "your_custom_verify_token"  # Generate any random string
```

Make sure these are added to `settings.py`:

```python
INSTAGRAM_CLIENT_ID = config('INSTAGRAM_CLIENT_ID')
INSTAGRAM_CLIENT_SECRET = config('INSTAGRAM_CLIENT_SECRET')
INSTAGRAM_REDIRECT_URI = config('INSTAGRAM_REDIRECT_URI')
INSTAGRAM_VERIFY_TOKEN = config('INSTAGRAM_VERIFY_TOKEN')
```

### Step 2: Create Database Migration

```bash
python manage.py makemigrations creator_dashboard
python manage.py migrate creator_dashboard
```

This creates the `InstagramWebhookEvent` table in your database.

### Step 3: Get Instagram Business Account Connected

Users must authenticate with their Instagram account first:

**Endpoint**: `POST /v1/plartform/instragram/auth/`

This returns the Instagram OAuth URL. After successful authentication, the callback will:
- Save their access token
- Store their Instagram account ID
- Store profile metadata including the IG account ID (required for webhook matching)

### Step 4: Get Your Webhook URL

**Endpoint**: `GET /v1/plartform/instragram/webhook/info/` (requires authentication)

This returns:
```json
{
  "webhook_url": "https://your-domain.com/v1/plartfrom/instagram/webhook/",
  "verify_token": "your_custom_verify_token",
  "instructions": "Configure this webhook URL in your Facebook App..."
}
```

### Step 5: Configure Webhook in Facebook Developer Console

1. Go to [Facebook Developer Console](https://developers.facebook.com/)
2. Select your app
3. Go to **Instagram** product → **Webhooks** (or **Settings** → **Basic** → **Webhooks**)
4. Click **Edit Subscription** or **Add Webhook**
5. Fill in the webhook fields:
   - **Callback URL**: `https://your-domain.com/v1/plartfrom/instagram/webhook/`
   - **Verify Token**: Your custom token from `INSTAGRAM_VERIFY_TOKEN`
   - **Subscription Fields**: Select the events you want to receive:
     - `media` - For post/media events
     - `comments` - For comment events
     - `likes` - For like events
     - `stories` - For story events

6. Click **Verify and Save**

### Step 6: Subscribe Your Instagram Business Account to Webhook

After saving the webhook, you need to subscribe your Instagram business account to receive events.

Use the Meta Graph API:

```bash
curl -X POST "https://graph.facebook.com/v19.0/{PAGE_ID}/subscribed_apps" \
  -d "access_token={PAGE_ACCESS_TOKEN}"
```

Or use this Python snippet:

```python
import requests

page_id = "your_page_id"  # Get from profile.meta['instagram']['page_id']
access_token = "your_access_token"

response = requests.post(
    f"https://graph.facebook.com/v19.0/{page_id}/subscribed_apps",
    params={"access_token": access_token}
)

print(response.json())
```

---

## How It Works

### Webhook Flow

```
1. User takes action on Instagram (like, comment, post, etc.)
   ↓
2. Instagram sends webhook to your endpoint: 
   POST /v1/plartfrom/instagram/webhook/
   ↓
3. Webhook view receives POST request with event data
   ↓
4. Extracts Instagram account ID from webhook data
   ↓
5. Finds the associated CreatorProfile using IG account ID
   ↓
6. Calls process_instagram_webhook_event() from service.py
   ↓
7. InstagramWebhookEvent record is created and saved to database
   ↓
8. ProfileVideos model is updated with latest stats
   ↓
9. Returns 200 OK to Instagram
```

### Webhook Event Structure

Instagram sends data in this format:

```json
{
  "entry": [
    {
      "id": "1234567890",  // Instagram business account ID
      "changes": [
        {
          "value": {
            "media_id": "17999999999999999",
            "caption": "Photo caption",
            "like_count": 42,
            "comments_count": 5,
            "timestamp": "2024-01-01T10:30:00+0000",
            "view_count": 150
          },
          "field": "media"
        }
      ]
    }
  ]
}
```

---

## Database Models

### InstagramWebhookEvent

Stores all incoming webhook events with the following fields:

```python
class InstagramWebhookEvent(models.Model):
    profile = ForeignKey(CreatorProfile)  # User's creator profile
    media_id = CharField()                 # Instagram media ID
    event_type = CharField()               # post|like|comment|view|share
    
    # Event data
    caption = TextField()                  # Media caption
    like_count = IntegerField()           # Number of likes
    comment_count = IntegerField()        # Number of comments
    view_count = IntegerField()           # Number of views
    comment_text = TextField()            # Comment content (if comment event)
    commenter_id = CharField()            # Who commented (if comment event)
    reaction_type = CharField()           # love|haha|wow|sad|angry (if reaction)
    
    # Metadata
    raw_webhook_data = JSONField()        # Original webhook payload
    timestamp = DateTimeField()           # When the action happened
    created_at = DateTimeField()          # When saved to DB
    updated_at = DateTimeField()          # Last update
```

---

## Using the Webhook Data

### View Events in Admin

1. Go to Django Admin: `/admin/creator_dashboard/instagramwebhookevent/`
2. Filter by event type, timestamp, or user
3. View raw webhook data in the "Metadata" section

### Query Events Programmatically

```python
from apps.creator_dashboard.models import InstagramWebhookEvent

# Get all events for a user
events = InstagramWebhookEvent.objects.filter(
    profile__user=request.user
).order_by('-timestamp')

# Get only likes
likes = InstagramWebhookEvent.objects.filter(
    profile__user=request.user,
    event_type='like'
).order_by('-timestamp')

# Get comments with text
comments = InstagramWebhookEvent.objects.filter(
    profile__user=request.user,
    event_type='comment'
).exclude(comment_text__isnull=True)

# Count events by type
from django.db.models import Count
event_counts = InstagramWebhookEvent.objects.filter(
    profile__user=request.user
).values('event_type').annotate(count=Count('id'))
```

### Create a Webhook Events API

Add this to your `views.py`:

```python
class UserInstagramWebhookEventsView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile = CreatorProfile.objects.get(user=request.user)
        events = InstagramWebhookEvent.objects.filter(
            profile=profile
        ).order_by('-timestamp')[:50]  # Last 50 events
        
        data = {
            'total': events.count(),
            'events': [
                {
                    'id': e.id,
                    'type': e.event_type,
                    'media_id': e.media_id,
                    'timestamp': e.timestamp.isoformat(),
                    'likes': e.like_count,
                    'comments': e.comment_count,
                    'caption': e.caption
                }
                for e in events
            ]
        }
        
        return self.success_response(data=data, status_code=200)
```

---

## Troubleshooting

### Webhooks Not Received

1. **Check webhook URL is publicly accessible**
   ```bash
   curl https://your-domain.com/v1/plartfrom/instagram/webhook/
   # Should return 403 (no valid token in GET request)
   ```

2. **Verify the verify_token matches**
   - Ensure `INSTAGRAM_VERIFY_TOKEN` in settings matches the token in Facebook console

3. **Check subscription is active**
   - Verify via Graph API: `GET /PAGE_ID/subscribed_apps`

4. **Check webhook logs**
   - In Django: Check console output and error logs
   - In Facebook console: Go to Webhooks → View logs

### No Profile Found

If you see "Profile not found for IG account: xxx":

1. Ensure user authenticated with Instagram (step 3)
2. Check `profile.meta['instagram']['ig_account_id']` exists in database:
   ```python
   from apps.creator_dashboard.models import CreatorProfile
   profile = CreatorProfile.objects.get(user=user)
   print(profile.meta.get('instagram'))
   ```

3. Verify the Instagram account ID in webhook matches stored ID

### Events Not Saving

1. Check Django error logs for exceptions
2. Ensure database migrations ran: `python manage.py showmigrations creator_dashboard`
3. Check Instagram App has required permissions

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/plartform/instragram/auth/` | POST | Get Instagram OAuth URL |
| `/v1/plartform/instragram/callback/` | GET | OAuth callback handler |
| `/v1/plartfrom/instagram/webhook/` | GET/POST | Webhook endpoint (no auth) |
| `/v1/plartform/instragram/webhook/info/` | GET | Get webhook URL & token info |

---

## Security Best Practices

1. **Verify webhook signature** (optional):
   ```python
   import hmac
   import hashlib
   
   def verify_webhook_signature(request, app_secret):
       signature = request.META.get('HTTP_X_HUB_SIGNATURE', '')
       body = request.body
       
       expected_signature = 'sha1=' + hmac.new(
           app_secret.encode(),
           body,
           hashlib.sha1
       ).hexdigest()
       
       return hmac.compare_digest(signature, expected_signature)
   ```

2. **Rate limiting**: Implement rate limiting on webhook endpoint
3. **Validation**: Always validate that the profile exists before processing
4. **Logging**: Log all webhook processing for auditing

---

## Next Steps

1. ✅ Deploy migrations to production
2. ✅ Configure webhook in Facebook console
3. ✅ Test webhook with sample events
4. ✅ Monitor webhook logs for errors
5. ✅ Create API endpoints to query webhook events
6. ✅ Build dashboards showing Instagram analytics

---

## Support & Debugging

For detailed logs, enable Django debug logging:

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
```

Then check webhook processing in console output.
