# 🚀 Instagram Webhook - Quick Start (5 Minutes)

## TL;DR - What You Need to Do

Your Instagram webhook integration is **ready to go**! Follow these steps:

### Step 1: Create Migration (1 minute)

```bash
cd c:\Users\Ridwan Islam\Desktop\projects\hairline_artist_django
python manage.py makemigrations creator_dashboard
python manage.py migrate creator_dashboard
```

### Step 2: Add Environment Variables (1 minute)

Add to your `.env` or `settings.py`:

```python
INSTAGRAM_CLIENT_ID = "your_client_id_from_facebook"
INSTAGRAM_CLIENT_SECRET = "your_secret_from_facebook"
INSTAGRAM_REDIRECT_URI = "https://your-domain.com/v1/plartform/instragram/callback/"
INSTAGRAM_VERIFY_TOKEN = "random_string_like_abc123xyz"
```

### Step 3: Configure Facebook Webhook (2 minutes)

1. Go to [Facebook Developer Console](https://developers.facebook.com/)
2. Select your app
3. Go to **Instagram** → **Webhooks**
4. Enter:
   - **Callback URL**: `https://your-domain.com/v1/plartfrom/instagram/webhook/`
   - **Verify Token**: Same value as `INSTAGRAM_VERIFY_TOKEN` above
5. Select fields: `media`, `comments`, `likes`, `stories`
6. Click **Verify and Save**

### Step 4: Subscribe Instagram Account (1 minute)

After user authenticates with Instagram, run:

```python
import requests

# Get from database after user authenticates
page_id = "facebook_page_id"
access_token = "user_access_token"

response = requests.post(
    f"https://graph.facebook.com/v19.0/{page_id}/subscribed_apps",
    params={"access_token": access_token}
)
print(response.json())  # Should show {"success": true}
```

---

## What Happens Now? ✨

### Before (Without Webhooks)
❌ You have to manually poll Instagram API  
❌ Miss real-time updates  
❌ Waste API quota  

### After (With Webhooks) ✅
✅ Instagram tells YOU when things happen  
✅ Real-time event tracking  
✅ Automatic database saving  
✅ No polling needed  

---

## Event Flow

```
User does something on Instagram
↓
Instagram posts to your webhook
↓
Your app receives the event
↓
Database saves the action
↓
Event visible in your admin + database
```

---

## What's Saved in Database?

When Instagram sends a webhook, this is automatically saved:

```json
{
  "media_id": "123456789",
  "event_type": "like",           // post, like, comment, view, share
  "caption": "Check this out!",
  "like_count": 42,
  "comment_count": 5,
  "view_count": 1000,
  "timestamp": "2024-01-01T10:30:00",
  "comment_text": "Amazing!",    // if comment event
  "commenter_id": "987654",      // if comment event
  "reaction_type": "love"        // if reaction
}
```

---

## Test It Works

### Test 1: Verify Webhook Configuration

```bash
curl -X GET "https://your-domain.com/v1/plartfrom/instagram/webhook/?hub.mode=subscribe&hub.verify_token=abc123xyz&hub.challenge=test123"

# Should return: test123
```

### Test 2: Check Events in Admin

1. Go to: `https://your-domain.com/admin/`
2. Find: **Creator Dashboard** → **Instagram Webhook Events**
3. Should show events after they happen

### Test 3: Query Events from Code

```python
from apps.creator_dashboard.models import InstagramWebhookEvent

# Get all events
events = InstagramWebhookEvent.objects.all()

# Get events for specific user
events = InstagramWebhookEvent.objects.filter(profile__user=user)

# Get only likes
likes = InstagramWebhookEvent.objects.filter(event_type='like')

# Count by type
event_counts = InstagramWebhookEvent.objects.values('event_type').count()
```

---

## Common Problems & Fixes

### "Profile not found for IG account"

**Problem**: User needs to authenticate with Instagram first

**Fix**:
1. User calls: `POST /v1/plartform/instragram/auth/`
2. Gets Instagram OAuth URL
3. Authorizes
4. Callback saves Instagram account ID
5. Now webhooks will work

### "Webhooks not received"

**Problem**: Facebook can't reach your endpoint

**Fix**:
1. Verify URL is publicly accessible
2. Test with: `curl https://your-domain.com/v1/plartfrom/instagram/webhook/`
3. Should get 403 (not authenticated)
4. Check Facebook webhook logs

### "ImportError: InstagramWebhookEvent"

**Problem**: Migration not applied

**Fix**:
```bash
python manage.py migrate creator_dashboard
```

---

## Files Changed

✅ **models.py** - Added InstagramWebhookEvent model  
✅ **service.py** - Added webhook processing functions  
✅ **views.py** - Enhanced webhook handling  
✅ **urls.py** - Added webhook info endpoint  
✅ **admin.py** - Registered models  
✅ **serializers.py** - Added serializers  

---

## Full Documentation

- 📖 **INSTAGRAM_WEBHOOK_SETUP.md** - Complete guide (900 lines)
- 📖 **INSTAGRAM_WEBHOOK_EXAMPLES.md** - Code examples (400 lines)
- 📖 **CODE_REVIEW.md** - Technical details (300 lines)

---

## Architecture Overview

```
Instagram Action
    ↓
Webhook POST request
    ↓
/v1/plartfrom/instagram/webhook/ endpoint
    ↓
Extract Instagram account ID
    ↓
Find CreatorProfile in database
    ↓
Call process_instagram_webhook_event() service
    ↓
Create InstagramWebhookEvent record
    ↓
Update ProfileVideos stats
    ↓
Return 200 OK
    ↓
Event visible in:
  - Django Admin
  - Database queries
  - API endpoints
```

---

## API Endpoints Created

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/plartform/instragram/auth/` | POST | Get Instagram auth URL |
| `/v1/plartform/instragram/callback/` | GET | OAuth callback |
| `/v1/plartfrom/instagram/webhook/` | GET/POST | Webhook receiver |
| `/v1/plartform/instragram/webhook/info/` | GET | Get webhook config |

---

## Database Schema

**New Table**: `creator_dashboard_instagramwebhookevent`

Stores:
- Profile link
- Media ID
- Event type (post, like, comment, view, share)
- Engagement counts
- Comment details
- Reaction type
- Raw webhook data
- Timestamps

---

## Next: Create Endpoints to Use Events

Example: Show user their Instagram events

```python
# Add to views.py
class UserInstagramEventsView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from apps.creator_dashboard.models import InstagramWebhookEvent, CreatorProfile
        from apps.creator_dashboard.serializers import InstagramWebhookEventSerializer
        
        profile = CreatorProfile.objects.get(user=request.user)
        events = InstagramWebhookEvent.objects.filter(profile=profile)[:50]
        
        return self.success_response(
            data=InstagramWebhookEventSerializer(events, many=True).data
        )

# Add to urls.py
path('v1/user/instagram/events/', UserInstagramEventsView.as_view())
```

---

## Summary

✅ **Migration**: Ready to run  
✅ **Code**: Fully implemented  
✅ **Security**: Properly secured  
✅ **Admin**: Complete interface  
✅ **Documentation**: Comprehensive  
✅ **Examples**: Available  

**You're 5 minutes away from real-time Instagram event tracking!** 🎉

---

## Questions?

Refer to:
- `INSTAGRAM_WEBHOOK_SETUP.md` - Full setup guide
- `INSTAGRAM_WEBHOOK_EXAMPLES.md` - Code examples  
- `CODE_REVIEW.md` - Technical reference
- `IMPLEMENTATION_SUMMARY.md` - Complete overview

**Deploy with confidence!** ✨
