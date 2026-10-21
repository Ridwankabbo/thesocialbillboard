# Google Login with User Type Selection

## Overview
The Google login endpoint now requires users to specify their `user_type` (either `parent` or `creator`) when logging in for the first time.

## API Endpoint
```
POST /api/google/
```

## Request Body
```json
{
  "access_token": "your_google_access_token",
  "user_type": "parent"  // or "creator" - REQUIRED for new users
}
```

## Response Flow

### Success (Returning User or New User with user_type)
**Status: 200 OK**
```json
{
  "success": true,
  "message": "Login successful",
  "status": 200,
  "data": {
    "tokens": {
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    },
    "profile": {
      "id": 1,
      "email": "user@gmail.com",
      "name": "John Doe",
      "user_type": "creator",
      "profile_pic": "https://...",
      "is_active": true
    }
  }
}
```

### User Type Required (New User without user_type)
**Status: 400 BAD REQUEST**
```json
{
  "success": false,
  "message": "user_type is required for new users",
  "status": 400,
  "data": {
    "user_types": [
      {"value": "parent", "label": "Parent"},
      {"value": "creator", "label": "Creator"}
    ],
    "user_id": 1,
    "email": "user@gmail.com",
    "name": "John Doe"
  }
}
```

### Invalid User Type
**Status: 400 BAD REQUEST**
```json
{
  "success": false,
  "message": "Invalid user_type. Must be one of: parent, creator",
  "status": 400
}
```

## Frontend Implementation

### Step 1: Get Google Access Token
```javascript
// Using Google Sign-In SDK
const response = await gapi.auth2.getAuthInstance().signIn();
const accessToken = response.getAuthResponse().id_token;
```

### Step 2: First Login Attempt (without user_type)
```javascript
const response = await fetch('/api/google/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    access_token: googleAccessToken
  })
});

const data = await response.json();

// If user_type is required
if (response.status === 400 && data.data?.user_types) {
  // Show user type selection dialog
  showUserTypeSelectionDialog(data.data.user_types);
}
```

### Step 3: Show User Type Selection (on 400 response)
```javascript
function showUserTypeSelectionDialog(userTypes) {
  // Display radio buttons or dropdown for:
  // - Parent: For users managing/monitoring creators
  // - Creator: For content creators

  const selectedUserType = await getUserTypeSelection(userTypes);
  
  // Re-send with user_type
  await loginWithUserType(googleAccessToken, selectedUserType);
}
```

### Step 4: Retry with User Type
```javascript
async function loginWithUserType(accessToken, userType) {
  const response = await fetch('/api/google/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      access_token: accessToken,
      user_type: userType  // 'parent' or 'creator'
    })
  });

  if (response.ok) {
    const data = await response.json();
    // Store tokens
    localStorage.setItem('access_token', data.data.tokens.access);
    localStorage.setItem('refresh_token', data.data.tokens.refresh);
    // Redirect to dashboard
    window.location.href = '/dashboard';
  }
}
```

## How It Works

1. **First Request without user_type**: 
   - If user already exists → Login succeeds (returns 200)
   - If user is new → Returns 400 with available user_type options

2. **Show Selection Dialog**: 
   - Display options to user (Parent or Creator)
   - Let them choose their role

3. **Second Request with user_type**: 
   - Set the user_type on the user account
   - Create JWT tokens
   - Return success response

## User Type Definitions

- **Parent**: For guardians or users who are monitoring/managing creators
- **Creator**: For content creators (YouTubers, TikTokers, Instagrammers, etc.)

## Notes

- Existing users' user_type won't be changed on subsequent logins
- The system automatically downloads and saves Google profile picture
- OTP verification is skipped for social login users
- Tokens are created immediately after authentication
