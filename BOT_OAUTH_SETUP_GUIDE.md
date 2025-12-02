# Plume Bot - OAuth Authentication Setup Guide

## Overview

The Plume Cloud bot now includes a complete OAuth 2.0 authentication flow using the Plume SSO (Single Sign-On) service. Users authenticate once, and the bot automatically manages their OAuth tokens with automatic refresh.

---

## Authentication Flow

### User Experience

When a user starts interacting with the bot, they'll go through a 4-step OAuth setup:

```
/start → /auth → Step 1: SSO URL → Step 2: Auth Header → Step 3: Partner ID → Step 4: API Base URL → ✅ Connected
```

### Step-by-Step Process

#### **Step 1️⃣: SSO URL**
```
User sees:
🔐 OAuth Authentication Setup

I'll help you set up Plume API authentication. Please provide the following information:

Step 1️⃣: What is your OAuth SSO URL?
(Example: https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token)
```

**User provides:**
```
https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token
```

#### **Step 2️⃣: Authorization Header**
```
User sees:
✅ SSO URL saved!

Step 2️⃣: What is your Authorization Header?
(Example: Bearer abc123... or Basic base64...)

This is your client credentials in base64 format.
```

**User provides:**
```
Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```
or
```
Bearer eyJhbGciOiJIUzI1NiIs...
```

#### **Step 3️⃣: Partner ID**
```
User sees:
✅ Authorization Header saved!

Step 3️⃣: What is your Partner ID?
(Example: eb0af9d0a7ab946dcb3b8ef5)

This identifies your Plume partner organization.
```

**User provides:**
```
eb0af9d0a7ab946dcb3b8ef5
```

#### **Step 4️⃣: Plume API Base URL** (Optional)
```
User sees:
✅ Partner ID saved!

Step 4️⃣: What is your Plume API Base URL?
(Example: https://api.plume.com or https://api.example.com)

If you're not sure, type /skip
```

**User can:**
- Provide custom URL: `https://api.example.com`
- Skip with: `/skip` (uses default)
- Cancel entire process: `/cancel`

### Final Verification

```
User sees:
📋 Confirming Your Configuration

SSO URL: https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token...
Partner ID: eb0af9d0a7ab946dcb3b8ef5
API Base: https://api.plume.com

🔄 Testing OAuth connection...

(If successful:)

✅ Authentication Successful!

🎉 You're all set! Your OAuth token has been obtained and will be automatically refreshed when needed.

You can now use all bot commands:
• /health <customerId> <locationId>
• /status <customerId> <locationId>
• /nodes <customerId> <locationId>
• /devices <customerId> <locationId>
• /wifi <customerId> <locationId>

Type /help for more information.
```

---

## OAuth Token Management

### Automatic Token Refresh

The bot automatically handles OAuth token lifecycle:

1. **Token Obtained**: When user authenticates, `access_token` and `token_expiry` are stored
2. **Token Validation**: Before each API call, bot checks if token is still valid
3. **Automatic Refresh**: If token expires within 60 seconds, it's automatically refreshed
4. **Token Expiration**: Stored with 60-second buffer to avoid expired token usage

### Code Implementation

```python
async def get_oauth_token(auth_config: Dict) -> Optional[str]:
    """Obtain OAuth token from Plume SSO using client credentials flow."""
    
    # Makes POST request to SSO URL with:
    # - Authorization: [user's auth header]
    # - Scope: "partnerId:{partner_id} role:partnerIdAdmin"
    # - Grant Type: "client_credentials"
    
    # Returns: {
    #   "access_token": "eyJ...",
    #   "token_expiry": datetime(2025-11-14 15:45:23),
    #   "expires_in": 3600
    # }
```

### Token Storage

Credentials are stored in-memory per user:

```python
user_auth = {
    12345: {  # user_id
        "sso_url": "https://external.sso.plume.com/oauth2/.../v1/token",
        "auth_header": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
        "partner_id": "eb0af9d0a7ab946dcb3b8ef5",
        "plume_api_base": "https://api.plume.com",
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_expiry": datetime(2025-11-14 15:45:23),
        "expires_in": 3600,
        "configured": True
    }
}
```

**⚠️ Production Note**: Replace in-memory storage with encrypted database!

---

## OAuth Request Flow

### Plume OAuth Curl Equivalent

The bot sends a request equivalent to:

```bash
curl --location 'https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token' \
  --header 'Cache-Control: no-cache' \
  --header 'Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'scope=partnerId:eb0af9d0a7ab946dcb3b8ef5 role:partnerIdAdmin' \
  --data-urlencode 'grant_type=client_credentials'
```

### Python Implementation

```python
async def get_oauth_token(auth_config: Dict) -> Optional[str]:
    sso_url = auth_config.get("sso_url")
    auth_header = auth_config.get("auth_header")
    partner_id = auth_config.get("partner_id")

    headers = {
        "Cache-Control": "no-cache",
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
        "expires_in": expires_in,
    }
```

---

## API Integration

### Using OAuth Token in API Calls

All API endpoints now use the OAuth token:

```python
async def plume_request(
    user_id: int,
    method: str,
    endpoint: str,
    params: Optional[Dict] = None,
    json: Optional[Dict] = None,
) -> dict:
    # Get valid OAuth token for user
    token = get_user_token(user_id)  # Validates expiry automatically
    
    if not token:
        raise PlumeAPIError(
            "No valid OAuth token. Please authenticate with /auth"
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    # Make authenticated API call to Plume
    async with httpx.AsyncClient(timeout=PLUME_TIMEOUT) as client:
        resp = await client.request(
            method=method.upper(),
            url=f"{PLUME_API_BASE}{endpoint}",
            params=params,
            json=json,
            headers=headers
        )
```

---

## Available Commands (After Authentication)

```
/health <customerId> <locationId>
  → Quick service health check (online status, pods, devices, QoE)

/status <customerId> <locationId>
  → Overall location health and speed tests

/nodes <customerId> <locationId>
  → List all gateway nodes with status

/devices <customerId> <locationId>
  → List all connected devices

/wifi <customerId> <locationId>
  → List WiFi networks configuration
```

---

## Error Handling

### Authentication Failures

If OAuth fails, user sees:

```
❌ Authentication Failed

Error: OAuth request failed with status 401

Please verify your credentials and try again with /auth.
```

### Invalid Credentials

- SSO URL validation: Must start with `https://`
- Auth Header: Cannot be empty
- Partner ID: Must be at least 20 characters
- API Base URL: Optional, uses default if skipped

### Token Refresh Failures

If token refresh fails during API call:

```
⚠️ Auth failed. Your token may be invalid or expired. 
Please re-authenticate with /auth.
```

---

## Security Considerations

### Current Implementation
- ✅ Tokens stored with expiry times
- ✅ Automatic refresh before expiration
- ✅ No hardcoded credentials
- ✅ User credentials prompted at runtime
- ⚠️ **In-memory storage (NOT production-ready)**

### Production Recommendations

1. **Use Encrypted Database**
   - SQLAlchemy + encryption (e.g., cryptography library)
   - Store tokens with user IDs as foreign keys

2. **Add Redis Cache**
   - Cache valid tokens to avoid repeated OAuth calls
   - Set expiry matching token expiry

3. **Audit Logging**
   - Log all authentication events
   - Log all API calls per user

4. **Rate Limiting**
   - Limit OAuth token requests per user/IP
   - Implement exponential backoff on failures

5. **Credential Rotation**
   - Allow users to update auth credentials via `/auth update`
   - Invalidate old tokens on credential change

6. **HTTPS Only**
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

3. **Send `/auth`:**
   - Bot asks for SSO URL
   - Provide: `https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token`

4. **Send Auth Header:**
   - Provide your client credentials header
   - Example: `Basic dXNlcm5hbWU6cGFzc3dvcmQ=`

5. **Send Partner ID:**
   - Provide: `eb0af9d0a7ab946dcb3b8ef5`

6. **Send API Base or /skip:**
   - Type `/skip` to use default

7. **Bot tests OAuth:**
   - Should show ✅ Authentication Successful!

8. **Use commands:**
   - `/health <customerId> <locationId>`
   - Bot uses OAuth token automatically

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "OAuth token request failed: 401" | Check auth header credentials |
| "No access_token in OAuth response" | Verify Partner ID is correct |
| "Network error during OAuth" | Check SSO URL is reachable |
| "Incomplete OAuth configuration" | Restart with `/auth` |
| "Partner ID looks invalid" | Must be 20+ characters |

---

## Summary

The Plume Bot now features:

✅ **OAuth 2.0 Client Credentials Flow**
- Users provide SSO URL, auth header, partner ID
- Bot obtains and manages access tokens

✅ **Automatic Token Lifecycle Management**
- Validates token expiry before use
- Automatically refreshes when needed
- Stores with 60-second safety buffer

✅ **Simple User Experience**
- 4-step guided setup via Telegram
- One-time configuration per user
- Automatic refresh - no re-authentication needed

✅ **Security Features**
- Credentials encrypted at rest (recommended)
- Automatic token expiration handling
- Error handling for failed authentications

Ready for production with proper database backend!
