# Panoptes Bot - Quick Reference Guide

**Version:** 1.0  
**Last Updated:** December 2024

## Getting Started

### Architecture Overview

```
User (Telegram)
    ↓
Telegram Bot (panoptes_bot.py)
    ├── Command Handlers (/start, /setup, /locations, /status, /wan, /stats, /nodes, /wifi)
    └── ConversationHandlers (/setup flow, /locations flow)
        ↓
    OAuth 2.0 Authentication (2-step process)
        ├── Authorization Header (client credentials)
        └── Partner ID (organization)
        ↓
    Plume API Client (plume_api_client.py)
        ├── get_nodes_in_location()
        ├── get_location_status()
        ├── get_wifi_networks()
        ├── get_wan_stats()
        ├── analyze_location_health()
        ├── analyze_wan_stats()
        └── format_wan_analysis()
        ↓
    Plume Cloud API (REST)
```

## Authentication Flow

### User Journey (2-Step Setup)

1. User sends `/setup` command
2. Bot enters ConversationHandler
3. **Step 1**: Bot asks for Authorization Header
   - User provides: `Basic base64encoded...`
4. **Step 2**: Bot asks for Partner ID
   - User provides: `eb0af9d0a7ab946dcb3b8ef5`
5. **Final**: Bot exchanges credentials for OAuth token
   - Success: Suggests running `/locations`
   - Failure: Prompts user to retry `/setup`

### OAuth 2.0 Client Credentials Flow

```
Client (Bot) sends to SSO:
  POST https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token
  Headers:
    Authorization: <user's auth header>
    Content-Type: application/x-www-form-urlencoded
  Body:
    grant_type=client_credentials&scope=partnerId:eb0af9d0a7ab946dcb3b8ef5 role:partnerIdAdmin

SSO responds with:
  {
    "access_token": "token_string",
    "token_type": "Bearer",
    "expires_in": 3600
  }

Bot stores token and uses for API calls:
  GET /api/Customers/{customerId}/locations/{locationId}
  Headers:
    Authorization: Bearer <access_token>
```

## Key Functions

### Authentication Helpers (plume_api_client.py)

| Function | Purpose | Returns |
|----------|---------|---------|
| `get_oauth_token()` | Exchange credentials for token | OAuth token dict |
| `set_user_auth()` | Store user's OAuth configuration | None |
| `get_user_auth()` | Retrieve user's OAuth config | Dict or None |
| `is_oauth_token_valid()` | Check if token is still valid | Boolean |

### API Wrappers (plume_api_client.py)

| Function | Purpose |
|----------|---------|
| `plume_request()` | Generic authenticated API call |
| `get_customers()` | Get all customers for partner |
| `get_locations_for_customer()` | Get locations for a customer |
| `get_nodes_in_location()` | Get pods in a location |
| `get_location_status()` | Get location health info |
| `get_wifi_networks()` | Get WiFi SSIDs |
| `get_wan_stats()` | Get WAN consumption data |

### Analysis Functions (plume_api_client.py)

| Function | Purpose |
|----------|---------|
| `analyze_location_health()` | Generate health report from location/node data |
| `analyze_wan_stats()` | Analyze WAN stats for consumption metrics |
| `format_wan_analysis()` | Format WAN analysis into user-friendly report |

### Command Handlers (panoptes_bot.py)

| Command | Handler | Description |
|---------|---------|-------------|
| `/start` | `start()` | Welcome message, guides to next step |
| `/setup` | `setup_start()` | OAuth setup wizard (2 steps) |
| `/locations` | `locations_start()` | Customer/location selection |
| `/status` | `status()` | Main health dashboard with action buttons |
| `/wan` | `wan_command()` | WAN consumption report |
| `/stats` | `stats_command()` | Online stats with time range selection |
| `/nodes` | `nodes()` | Detailed pod information |
| `/wifi` | `wifi()` | WiFi network listing |

### Conversation States

| State | Constant | What It Does |
|-------|----------|--------------|
| 0 | `ASK_AUTH_HEADER` | Waiting for Authorization Header |
| 1 | `ASK_PARTNER_ID` | Waiting for Partner ID |
| 0 | `ASK_CUSTOMER_ID` | Waiting for Customer ID |
| 1 | `SELECT_LOCATION` | Waiting for location selection |

## Code Organization

### File Structure

```
panoptes_bot.py
├── Module Docstring
├── Imports
├── Configuration & Logging
├── Conversation States
├── Error Handler
├── Helper Functions (get_reply_source, format_speed_test, format_pod_details)
├── Command Handlers (start, status, nodes, wifi, wan_command)
├── Navigation Callback Handler
├── Location Selection Conversation
├── Auth Setup Conversation (2-step)
└── Main Bot Setup

plume_api_client.py
├── Configuration & Logging
├── Exceptions (PlumeAPIError)
├── Authentication Management
├── Plume API Client (plume_request)
├── API Wrappers
└── Service Health Analysis
```

### Data Flow

```
1. User Input (Telegram)
   ↓
2. Handler Function (extract arguments, validate)
   ↓
3. Authentication Check (is_oauth_token_valid)
   ↓
4. API Call (plume_api_client.py)
   ↓
5. Response Processing (analyze_location_health, etc.)
   ↓
6. Response Formatting (Markdown text)
   ↓
7. Send to User (Telegram)
```

## Development Workflow

### Adding a New Command Handler

1. **Create handler function in panoptes_bot.py**:
   ```python
   async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
       """
       /new command - What it does.
       """
       reply_source = get_reply_source(update)
       user_id = update.effective_user.id
       
       # 1. Check if location is selected
       if 'customer_id' not in context.user_data or 'location_id' not in context.user_data:
           await reply_source.reply_text("Please select a location with /locations first.")
           return
       
       # 2. Make API call
       try:
           result = await some_api_function(user_id, ...)
       except PlumeAPIError as e:
           await reply_source.reply_text(f"An API error occurred: {e}")
           return
       
       # 3. Format and send response
       await reply_source.reply_markdown(f"*Result*: {result}")
   ```

2. **Register handler in main()**:
   ```python
   application.add_handler(CommandHandler("new", new_command))
   ```

### Debugging Tips

1. **Check logs**: Search for user ID to trace execution
   ```
   logger.info("Processing command for user %s", user_id)
   ```

2. **Validate configuration**: 
   - Use `is_oauth_token_valid()` to check stored credentials
   - Verify OAuth token hasn't expired

3. **Test OAuth flow**:
   - Verify SSO URL returns token
   - Check Authorization header format
   - Validate Partner ID in OAuth scope

4. **API errors**:
   - All API calls raise `PlumeAPIError` with details
   - Check logs for HTTP status codes
   - Verify customerId and locationId parameters

## Security Considerations

### Credential Handling

- ✅ **Never log full credentials**: Log only length or type
- ✅ **Store in memory only**: Use global `user_auth` dict
- ✅ **Use HTTPS**: All API URLs must be HTTPS
- ✅ **Validate inputs**: Check URLs, IDs, headers before storing
- ✅ **Token expiration**: Automatically refresh before use

### Best Practices

1. Always validate user input before storing
2. Check authentication before API calls
3. Use try/catch for all API operations
4. Log errors without exposing sensitive data
5. Clear configuration on auth failure

## Testing Checklist

- [ ] OAuth token exchange works
- [ ] Token auto-refresh on expiration
- [ ] All commands return valid data
- [ ] Error handling provides useful messages
- [ ] Conversation handler accepts `/cancel` at each step
- [ ] Unauthenticated users can't access commands
- [ ] Markdown formatting renders correctly in Telegram

## Common Issues

### "Authentication configuration incomplete"
- User didn't complete the 2-step OAuth setup
- Solution: Prompt user to run `/setup` again

### "Invalid OAuth token"
- Token expired and refresh failed
- Solution: Check token refresh logic, verify SSO endpoint
- User action: Re-run `/setup` to get new token

### "Plume API error: 401 Unauthorized"
- OAuth token not being sent or invalid format
- Solution: Check `Authorization: Bearer <token>` header format
- Verify token is refreshed before API request

### "Partner ID not found"
- Partner ID doesn't exist or has no access
- Solution: Verify Partner ID is correct
- Check if user has proper permissions in Plume organization

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot API token |
| `PLUME_API_BASE` | No | Plume API endpoint (default provided) |
| `PLUME_REPORTS_BASE` | No | Plume Reports API endpoint (default provided) |

## References

- [Python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [OAuth 2.0 Client Credentials Flow](https://tools.ietf.org/html/rfc6749#section-4.4)
- [Telegram Bot Commands](https://core.telegram.org/bots/api#sendmessage)
- [Markdown formatting in Telegram](https://core.telegram.org/bots/api#markdown-style)

---

**Version**: 1.0  
**Status**: Production Ready
