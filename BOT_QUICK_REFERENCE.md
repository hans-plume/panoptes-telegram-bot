# Plume Bot - Quick Reference

## User Authentication Flow

```
START
  ↓
/auth command
  ↓
User provides OAuth SSO URL
  ↓
User provides Authorization Header (Bearer or Basic)
  ↓
User provides Partner ID
  ↓
User provides API Base URL (or /skip)
  ↓
Bot tests OAuth connection
  ↓
✅ AUTHENTICATED - Ready to use all commands
```

## OAuth Configuration Example

```json
{
  "sso_url": "https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token",
  "auth_header": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
  "partner_id": "eb0af9d0a7ab946dcb3b8ef5",
  "plume_api_base": "https://api.plume.com"
}
```

## OAuth Request Details

**Endpoint:** User's SSO URL  
**Method:** POST  
**Headers:**
```
Cache-Control: no-cache
Authorization: [user's auth header]
Content-Type: application/x-www-form-urlencoded
```

**Parameters:**
```
scope: "partnerId:{partner_id} role:partnerIdAdmin"
grant_type: "client_credentials"
```

## Available Commands (After Auth)

| Command | Usage | Response |
|---------|-------|----------|
| `/health` | `/health <customerId> <locationId>` | 🏥 Service health status |
| `/status` | `/status <customerId> <locationId>` | 🏠 Location health overview |
| `/nodes` | `/nodes <customerId> <locationId>` | 📡 Gateway/pod list |
| `/devices` | `/devices <customerId> <locationId>` | 📱 Connected devices |
| `/wifi` | `/wifi <customerId> <locationId>` | 📶 WiFi networks |

## Token Management

```python
# Check token validity
is_oauth_token_valid(user_id: int) -> bool

# Get valid token (auto-refreshes if needed)
get_user_token(user_id: int) -> Optional[str]

# Refresh token
await get_oauth_token(auth_config: Dict) -> Dict

# Token expires in: 1 hour (default)
# Refresh triggered: 60 seconds before expiry
```

## Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| "Invalid URL" | SSO URL doesn't start with https:// | Use correct HTTPS URL |
| "Authorization header cannot be empty" | Missing auth header | Provide Bearer or Basic token |
| "Partner ID looks invalid" | Too short (<20 chars) | Verify Partner ID format |
| "OAuth token request failed: 401" | Bad credentials | Check auth header |
| "Auth failed. Your token may be invalid or expired" | Token expired or revoked | Run `/auth` again |

## Health Status Indicators

```
🟢 GREEN (ALL SYSTEMS OPERATIONAL)
  - Location online
  - All pods connected
  - All devices connected
  - Good QoE

🟡 YELLOW (DEGRADED SERVICE)
  - Some devices disconnected
  - Poor QoE on some traffic

🟠 ORANGE (SERVICE DISRUPTED)
  - Multiple pods disconnected
  - Service level affected

🔴 RED (LOCATION OFFLINE)
  - Entire location unreachable
  - No service available
```

## Code Integration Points

**Authentication Flow:**
```
/auth → ConversationHandler
  → ASK_SSO_URL → receive_sso_url()
  → ASK_AUTH_HEADER → receive_auth_header()
  → ASK_PARTNER_ID → receive_partner_id()
  → ASK_PLUME_API_BASE → receive_api_base()
  → confirm_auth() → OAuth token test
```

**API Calls:**
```
Command → get_user_token(user_id) → get valid token
       → plume_request() → API endpoint
       → Format response → Send to user
```

**Token Validation:**
```
Before each API call:
  - Check if token exists
  - Check if token_expiry > now + 60s
  - If invalid: Get new token via OAuth
```

## Production Checklist

- [ ] Replace in-memory token storage with encrypted DB
- [ ] Add Redis caching for valid tokens
- [ ] Implement audit logging for auth events
- [ ] Add rate limiting on OAuth requests
- [ ] Enable token rotation/invalidation
- [ ] Use HTTPS for all external calls
- [ ] Validate SSL certificates
- [ ] Implement credential update command
- [ ] Add token revocation on logout
- [ ] Monitor token refresh failures

---

**Bot Version:** 2.0 (OAuth Authentication)  
**Last Updated:** 2025-11-14  
**Status:** Ready for Testing
