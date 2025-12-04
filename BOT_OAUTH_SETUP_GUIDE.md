# Plume Bot - OAuth Authentication Setup Guide

**Version:** 1.0  
**Last Updated:** December 2024

## Overview

The Plume Cloud bot includes a complete OAuth 2.0 authentication flow using the Plume SSO (Single Sign-On) service. Users authenticate once using a simple 2-step process, and the bot automatically manages their OAuth tokens with automatic refresh.

---

## Authentication Flow

### User Experience

When a user starts interacting with the bot, they'll go through a 2-step OAuth setup:

```
/start → /setup → Step 1: Auth Header → Step 2: Partner ID → ✅ Connected → /locations
```

### Step-by-Step Process

#### **Step 1️⃣: Authorization Header**
```
User sends: /setup

Bot responds:
Starting OAuth setup...

**Step 1 of 2:** Please provide your Plume authorization header.
Send /cancel at any time to abort.
```

**User provides:**
```
Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```

#### **Step 2️⃣: Partner ID**
```
Bot responds:
**Step 2 of 2:** Great. Now, please provide your Plume Partner ID.
```

**User provides:**
```
eb0af9d0a7ab946dcb3b8ef5
```

### Final Verification

```
Bot responds:
Testing API connection...

(If successful:)
✅ **Success!** API connection is working.

Next, run /locations to begin.
```

```
(If failed:)
❌ **Failed!** [Error message]
Please run /setup again.
```

---

## OAuth Token Management

### Automatic Token Refresh

The bot automatically handles OAuth token lifecycle:

1. **Token Obtained**: When user authenticates, `access_token` and `token_expiry` are stored
2. **Token Validation**: Before each API call, bot checks if token is still valid
3. **Automatic Refresh**: If token expires within 60 seconds, it's automatically refreshed
4. **Token Expiration**: Stored with 60-second buffer to avoid expired token usage

### Token Storage

Credentials are stored in-memory per user:

```python
user_auth = {
    12345: {  # user_id
        "sso_url": "https://external.sso.plume.com/oauth2/.../v1/token",
        "auth_header": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
        "partner_id": "eb0af9d0a7ab946dcb3b8ef5",
        "plume_api_base": "https://piranha-gamma.prod.us-west-2.aws.plumenet.io/api/",
        "plume_reports_base": "https://piranha-gamma.prod.us-west-2.aws.plumenet.io/reports/",
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_expiry": datetime(2024-12-04 15:45:23),
    }
}
```

**⚠️ Production Note**: For production deployments, consider replacing in-memory storage with an encrypted database.

---

## OAuth Request Flow

### Plume OAuth Curl Equivalent

The bot sends a request equivalent to:

```bash
curl --location 'https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token' \
  --header 'Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'scope=partnerId:eb0af9d0a7ab946dcb3b8ef5 role:partnerIdAdmin' \
  --data-urlencode 'grant_type=client_credentials'
```

### Python Implementation (plume_api_client.py)

```python
async def get_oauth_token(auth_config: Dict) -> Dict:
    sso_url = auth_config.get("sso_url")
    auth_header = auth_config.get("auth_header")
    partner_id = auth_config.get("partner_id")

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "scope": f"partnerId:{partner_id} role:partnerIdAdmin",
        "grant_type": "client_credentials",
    }

    async with httpx.AsyncClient(timeout=PLUME_TIMEOUT) as client:
        resp = await client.post(sso_url, headers=headers, data=data)

    token_data = resp.json()
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in", 3600)
    
    # Store with 60-second buffer
    token_expiry = datetime.now() + timedelta(seconds=int(expires_in) - 60)
    
    return {
        "access_token": access_token,
        "token_expiry": token_expiry,
    }
```

---

## Available Commands (After Authentication)

```
/locations
  → Select customer and location to monitor

/status
  → Network health dashboard with action buttons

/wan
  → WAN consumption analytics (24-hour report)

/stats
  → Connection status history (3h, 24h, 7d views)

/nodes
  → Technical pod information

/wifi
  → WiFi network configuration
```

---

## Error Handling

### Authentication Failures

If OAuth fails, user sees:

```
❌ **Failed!** OAuth request failed with status 401

Please run /setup again.
```

### Token Refresh Failures

If token refresh fails during API call:

```
An API error occurred: Could not refresh token. Please re-authenticate with /setup.
```

---

## Security Considerations

### Current Implementation
- ✅ Tokens stored with expiry times
- ✅ Automatic refresh before expiration
- ✅ No hardcoded credentials
- ✅ User credentials prompted at runtime
- ✅ SSO URL hardcoded (secure default)
- ⚠️ **In-memory storage** (consider database for production)

### Production Recommendations

1. **Use Encrypted Database**
   - Store tokens with user IDs as foreign keys
   - Use encryption for sensitive fields

2. **Audit Logging**
   - Log all authentication events
   - Log all API calls per user

3. **Rate Limiting**
   - Limit OAuth token requests per user
   - Implement exponential backoff on failures

4. **HTTPS Only**
   - All OAuth flows over HTTPS
   - Validate SSL certificates

---

## Testing the OAuth Flow

### Manual Testing Steps

1. **Start the bot:**
   ```bash
   python panoptes_bot.py
   ```

2. **Send `/start`:**
   - Bot responds with welcome message

3. **Send `/setup`:**
   - Bot asks for Authorization Header

4. **Send Auth Header:**
   - Provide your client credentials header
   - Example: `Basic dXNlcm5hbWU6cGFzc3dvcmQ=`

5. **Send Partner ID:**
   - Provide: `eb0af9d0a7ab946dcb3b8ef5`

6. **Bot tests OAuth:**
   - Should show ✅ Success!

7. **Send `/locations`:**
   - Select a customer and location

8. **Use commands:**
   - `/status`, `/wan`, `/stats`, `/nodes`, `/wifi`
   - Bot uses OAuth token automatically

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "OAuth request failed: 401" | Check auth header credentials |
| "No access_token in OAuth response" | Verify Partner ID is correct |
| "Network error during OAuth" | Check SSO URL is reachable |
| "Could not refresh token" | Re-run `/setup` |

---

## Summary

The Plume Bot features:

✅ **Simplified 2-Step OAuth Setup**
- Users provide Authorization Header and Partner ID
- SSO URL uses secure default

✅ **Automatic Token Lifecycle Management**
- Validates token expiry before use
- Automatically refreshes when needed
- Stores with 60-second safety buffer

✅ **Simple User Experience**
- 2-step guided setup via Telegram
- One-time configuration per user
- Automatic refresh - no re-authentication needed

✅ **Guided Workflow**
- After setup: suggests `/locations`
- After location selection: suggests `/status`
- After status: provides quick action buttons

Ready for production with proper database backend!
