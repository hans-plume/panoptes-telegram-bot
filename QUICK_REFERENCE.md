# Panoptes Bot - Quick Reference Guide

## Getting Started

### Architecture Overview

```
User (Telegram)
    ↓
Telegram Bot (panoptes_bot.py)
    ├── Command Handlers (/start, /health, /status, etc.)
    └── ConversationHandler (/auth flow)
        ↓
    OAuth 2.0 Authentication
        ├── SSO URL (token endpoint)
        ├── Authorization Header (client credentials)
        ├── Partner ID (organization)
        └── Plume API Base URL (optional)
        ↓
    Plume API Client (plume_api_client.py)
        ├── get_nodes_in_location()
        ├── get_connected_devices()
        ├── get_location_status()
        ├── get_wifi_networks()
        ├── get_service_level()
        ├── get_qoe_stats()
        ├── get_internet_health()
        └── analyze_location_health()
        ↓
    Plume Cloud API (REST)
```

## Authentication Flow

### User Journey

1. User sends `/auth` command
2. Bot enters ConversationHandler
3. **Step 1**: Bot asks for OAuth SSO URL
   - User provides: `https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token`
4. **Step 2**: Bot asks for Authorization Header
   - User provides: `Bearer abc123xyz...` or `Basic base64encoded...`
5. **Step 3**: Bot asks for Partner ID
   - User provides: `eb0af9d0a7ab946dcb3b8ef5`
6. **Step 4**: Bot asks for Plume API Base URL (optional)
   - User provides: `https://api.plume.com` or `/skip` for default
7. **Final**: Bot exchanges credentials for OAuth token
   - Success: Shows available commands
   - Failure: Clears config and asks to retry

### OAuth 2.0 Client Credentials Flow

```
Client (Bot) sends to SSO:
  POST /oauth2/ausc034rgdEZKz75I357/v1/token
  Headers:
    Authorization: Bearer <base64_encoded_credentials>
    Content-Type: application/x-www-form-urlencoded
  Body:
    grant_type=client_credentials&scope=partner:eb0af9d0a7ab946dcb3b8ef5

SSO responds with:
  {
    "access_token": "token_string",
    "token_type": "Bearer",
    "expires_in": 3600
  }

Bot stores token and uses for API calls:
  GET /api/v2/locations/{customerId}/{locationId}/health
  Headers:
    Authorization: Bearer <access_token>
```

## Key Functions

### Authentication Helpers

| Function | Purpose | Returns |
|----------|---------|---------|
| `get_oauth_token()` | Exchange credentials for token | OAuth token dict |

### Command Handlers

| Command | Handler | Parameters | Returns |
|---------|---------|------------|---------|
| `/start` | `start()` | - | Welcome message |
| `/auth` | `auth_start()` | - | OAuth setup wizard |
| `/health` | `handle_health_command()` | `<customerId> <locationId>` | Quick health check |
| `/status` | `handle_status_command()` | `<customerId> <locationId>` | Location status |
| `/nodes` | `handle_nodes_command()` | `<customerId> <locationId>` | Node status |
| `/devices` | `handle_devices_command()` | `<customerId> <locationId>` | Device list |
| `/wifi` | `handle_wifi_command()` | `<customerId> <locationId>` | WiFi networks |

### Conversation States

| State | Constant | What It Does |
|-------|----------|--------------|
| 2 | `ASK_AUTH_HEADER` | Waiting for Bearer/Basic credentials |
| 3 | `ASK_PARTNER_ID` | Waiting for Partner ID |
| 4 | `ASK_PLUME_API_BASE` | Waiting for Plume API base URL (or skip) |

## Code Organization

### File Structure

```
panoptes_bot.py
├── Module Docstring
├── Imports
├── Configuration & Initialization
│   ├── Environment variables
│   ├── Logging setup
│   └── Conversation state constants
├── OAuth Helper Functions
│   ├── get_oauth_token()
│   ├── validate_auth_config()
│   └── ensure_valid_token()
├── Telegram Command Handlers
│   └── start()
├── OAuth Authentication Conversation Handler
│   ├── auth_start()
│   ├── receive_sso_url()
│   ├── receive_auth_header()
│   ├── receive_partner_id()
│   ├── receive_api_base()
│   ├── skip_api_base()
│   ├── confirm_auth()
│   └── auth_cancel()
├── Status Query Handlers
│   ├── handle_health_command()
│   ├── handle_nodes_command()
│   ├── handle_devices_command()
│   ├── handle_status_command()
│   └── handle_wifi_command()
└── Main Bot Setup
    ├── main()
    └── __main__ entry point
```

### Data Flow

```
1. User Input (Telegram)
   ↓
2. Handler Function (extract arguments, validate)
   ↓
3. Authentication Check (ensure_valid_token)
   ↓
4. API Call (plume_api_client.py)
   ↓
5. Response Formatting (Markdown text)
   ↓
6. Send to User (Telegram)
```

## Development Workflow

### Adding a New Command Handler

1. **Create handler function**:
   ```python
   async def handle_new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
       """
       /new command - What it does.
       
       Takes: <arg1> <arg2>
       Returns: Status message
       """
       user_id = update.effective_user.id
       
       # 1. Extract and validate arguments
       if len(context.args) < 2:
           await update.message.reply_text("Usage: /new <arg1> <arg2>")
           return
       
       # 2. Check authentication
       auth_config = user_auth.get(user_id)
       if not auth_config or not auth_config.get("configured"):
           await update.message.reply_text("Please authenticate first with /auth")
           return
       
       # 3. Make API call
       try:
           result = await some_api_function(arg1, arg2, auth_config)
       except PlumeAPIError as e:
           await update.message.reply_markdown(f"❌ Error: {e}")
           return
       
       # 4. Format response
       response = f"✅ Result:\n{result}"
       
       # 5. Send to user
       await update.message.reply_markdown(response)
   ```

2. **Register handler in main()**:
   ```python
   app.add_handler(CommandHandler("new", handle_new_command))
   ```

### Debugging Tips

1. **Check logs**: Search for user ID to trace execution
   ```
   logger.info("Processing command for user %s", user_id)
   ```

2. **Validate configuration**: 
   - Use `validate_auth_config()` to check stored credentials
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
- User didn't complete all 4 steps of OAuth setup
- Solution: Prompt user to run `/auth` again

### "Invalid OAuth token"
- Token expired and refresh failed
- Solution: Check token refresh logic, verify SSO endpoint
- User action: Re-run `/auth` to get new token

### "Plume API error: 401 Unauthorized"
- OAuth token not being sent or invalid format
- Solution: Check `Authorization: Bearer <token>` header format
- Verify `ensure_valid_token()` is called before API request

### "Partner ID not found"
- Partner ID doesn't exist or has no access
- Solution: Verify Partner ID is correct
- Check if user has proper permissions in Plume organization

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot API token |
| `PLUME_API_BASE` | No | Plume API endpoint (default provided) |

## References

- [Python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [OAuth 2.0 Client Credentials Flow](https://tools.ietf.org/html/rfc6749#section-4.4)
- [Telegram Bot Commands](https://core.telegram.org/bots/api#sendmessage)
- [Markdown formatting in Telegram](https://core.telegram.org/bots/api#markdown-style)

---

**Last Updated**: 2024
**Version**: 1.0
**Status**: Ready for development
