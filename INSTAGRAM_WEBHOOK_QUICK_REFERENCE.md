# Instagram Webhook Implementation - Quick Reference

## Summary of Changes

### 1. New Database Model
**File**: `apps/creator_dashboard/models.py`

Added `InstagramWebhookEvent` model to store:
- Event type (post, like, comment, view, share)
- Media ID and caption
- Like, comment, view counts
- Reaction type (for reactions)
- Comment text and commenter ID
- Raw webhook JSON data
- Timestamp of the action

### 2. Service Functions
**File**: `apps/creator_dashboard/service.py`

Added functions:
- `process_instagram_webhook_event(webhook_data, profile)` - Main processor
- `determine_event_type(webhook_value)` - Detects event type from data
- `parse_webhook_timestamp(timestamp_str)` - Converts timestamp
- `update_profile_video_stats(profile, media_id, webhook_value)` - Updates ProfileVideos
- `get_profile_from_ig_account(ig_account_id)` - Finds profile by IG account ID
- `get_profile_from_page_id(page_id)` - Alternative lookup by page ID

### 3. Webhook View
**File**: `apps/creator_dashboard/views.py`

Updated `instagram_webhook()` function:
- Handles GET requests for webhook verification
- Processes POST requests with webhook events
- Extracts Instagram account ID from webhook
- Finds associated CreatorProfile
- Calls service function to process and save events

Added `InstagramWebhookInfoView` class:
- Returns webhook URL and verify token for users
- Used to configure webhook in Facebook console

### 4. Admin Interface
**File**: `apps/creator_dashboard/admin.py`

Registered all models with custom admin classes:
- `CreatorProfileAdmin` - View creator profiles
- `CreatroCredentialsAdmin` - View stored tokens
- `ProfileVideosAdmin` - View video stats
- `InstagramWebhookEventAdmin` - View and filter webhook events

### 5. URLs
**File**: `apps/creator_dashboard/urls.py`

Added endpoint:
- `v1/plartform/instragram/webhook/info/` → `InstagramWebhookInfoView`

### 6. Updated Callback Service
**File**: `apps/creator_dashboard/service.py` (function: `instagram_callback_service`)

Now stores in `profile.meta['instagram']`:
- `ig_account_id` - The Instagram business account ID (required for webhook matching!)
- `page_id` - Facebook page ID (as backup)
- Profile data (username, followers, etc.)

---

## Critical Setup Steps

### 1. Create & Run Migration
```bash
python manage.py makemigrations creator_dashboard
python manage.py migrate
```

### 2. Add Environment Variables
```python
# .env or settings.py
INSTAGRAM_CLIENT_ID = "your_client_id"
INSTAGRAM_CLIENT_SECRET = "your_client_secret"
INSTAGRAM_REDIRECT_URI = "https://your-domain.com/v1/plartform/instragram/callback/"
INSTAGRAM_VERIFY_TOKEN = "generate_any_random_string"
```

### 3. User Flow
1. User clicks to authenticate Instagram
2. Gets redirected to Instagram OAuth
3. After auth, user's IG account ID is stored in `profile.meta['instagram']['ig_account_id']`
4. Webhook events now match to this profile

### 4. Configure Webhook in Facebook Console
- URL: `https://your-domain.com/v1/plartfrom/instagram/webhook/`
- Verify Token: Same as `INSTAGRAM_VERIFY_TOKEN`
- Fields: media, comments, likes, stories

### 5. Subscribe Account to Webhook
```python
# After user authenticates
requests.post(
    f"https://graph.facebook.com/v19.0/{page_id}/subscribed_apps",
    params={"access_token": access_token}
)
```

---

## How Webhooks Work Now

```
Instagram Action (post, like, comment, view, share)
        ↓
POST request to /v1/plartfrom/instagram/webhook/
        ↓
Extract IG account ID from webhook entry[0]['id']
        ↓
Find CreatorProfile where meta['instagram']['ig_account_id'] matches
        ↓
Call process_instagram_webhook_event(webhook_data, profile)
        ↓
Determine event type from data
        ↓
Create InstagramWebhookEvent record in database
        ↓
Update ProfileVideos with latest stats
        ↓
Return 200 OK to Instagram
```

---

## Testing Webhooks

### Test Webhook Verification
```bash
curl -X GET "http://localhost:8000/v1/plartfrom/instagram/webhook/?hub.mode=subscribe&hub.verify_token=your_verify_token&hub.challenge=test_challenge_string"
# Should return: test_challenge_string
```

### Test Event Processing
```bash
curl -X POST "http://localhost:8000/v1/plartfrom/instagram/webhook/" \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "id": "instagram_account_id",
      "changes": [{
        "value": {
          "media_id": "123456789",
          "caption": "Test post",
          "like_count": 5,
          "comments_count": 2,
          "timestamp": "2024-01-01T10:00:00+0000"
        }
      }]
    }]
  }'
# Should return 200 OK
```

---

## Database Queries

### Get all webhook events for a user
```python
from apps.creator_dashboard.models import InstagramWebhookEvent, CreatorProfile

profile = CreatorProfile.objects.get(user=user)
events = InstagramWebhookEvent.objects.filter(profile=profile).order_by('-timestamp')
```

### Get specific event type
```python
likes = InstagramWebhookEvent.objects.filter(
    profile=profile,
    event_type='like'
).order_by('-timestamp')

comments = InstagramWebhookEvent.objects.filter(
    profile=profile,
    event_type='comment'
)
```

### Get event statistics
```python
from django.db.models import Count, Sum

stats = InstagramWebhookEvent.objects.filter(
    profile=profile
).values('event_type').annotate(
    count=Count('id'),
    total_likes=Sum('like_count'),
    total_comments=Sum('comment_count')
)
```

---

## Common Issues & Fixes

### Issue: "Profile not found for IG account: xxx"
**Fix**: Ensure user has completed Instagram authentication. Check:
```python
profile = CreatorProfile.objects.get(user=user)
print(profile.meta)  # Should contain 'instagram' with 'ig_account_id'
```

### Issue: Webhooks not received
**Fix**: 
1. Verify webhook URL is publicly accessible
2. Verify token matches in Facebook console and settings
3. Ensure subscribed_apps endpoint was called
4. Check Facebook webhook logs for errors

### Issue: Events not saving to database
**Fix**:
1. Check migrations ran: `python manage.py showmigrations creator_dashboard`
2. Check for exceptions in Django logs
3. Verify raw_webhook_data contains expected fields

---

## API Endpoints Reference

| Path | Method | Auth | Purpose |
|------|--------|------|---------|
| `/v1/plartform/instragram/auth/` | POST | Required | Get Instagram OAuth URL |
| `/v1/plartform/instragram/callback/` | GET | None | Callback handler |
| `/v1/plartfrom/instagram/webhook/` | GET/POST | None | Webhook endpoint |
| `/v1/plartform/instragram/webhook/info/` | GET | Required | Get webhook config info |

---

## File Changes Summary

```
✅ models.py - Added InstagramWebhookEvent model
✅ service.py - Added 6 new webhook processing functions
✅ views.py - Updated webhook view + added webhook info view
✅ urls.py - Added webhook info endpoint
✅ admin.py - Registered all models with custom admin classes
```

All changes follow your existing code structure with core logic in `service.py` and views returning responses!
