# Plume Bot - Code Architecture

## Module Structure

```
panoptes_bot.py
├── Imports & Configuration
│   ├── httpx (async HTTP client)
│   ├── telegram (bot framework)
│   ├── datetime (token expiry)
│   └── ConversationHandler (OAuth flow)
│
├── Configuration
│   ├── TELEGRAM_BOT_TOKEN (from env)
│   ├── PLUME_API_BASE (from env or default)
│   ├── PLUME_TIMEOUT = 10 seconds
│   └── Logging setup
│
├── Conversation States (OAuth & Locations)
│   ├── (ASK_AUTH_HEADER, ASK_PARTNER_ID)
│   └── (ASK_CUSTOMER_ID, SELECT_LOCATION)
│
├── Authentication Management
│   ├── user_auth{} - Token storage
│   ├── set_user_auth(user_id, config)
│   ├── get_user_auth(user_id)
│   ├── is_oauth_token_valid(user_id)
│   └── get_oauth_token(auth_config)
│       └── POST to Plume SSO
│
├── Plume API Client
│   ├── PlumeAPIError - Custom exception
│   └── async plume_request()
│       ├── Manages token validation and refresh
│       └── Makes all authenticated API calls
│
├── API Wrapper Functions
│   ├── get_location_status()
│   ├── get_nodes_in_location()
│   └── get_wifi_networks()
│
├── Health Analysis
│   └── analyze_location_health()
│       └── Generates a rich health report dictionary
│
├── Response Formatters
│   ├── format_speed_test()
│   └── format_pod_details()
│
├── Conversation Handlers
│   ├── Setup Conversation (/setup)
│   └── Locations Conversation (/locations)
│
├── Command Handlers
│   ├── start() - Welcome message
│   ├── status() - Main health report
│   ├── nodes() - Detailed pod info
│   └── wifi() - WiFi SSID list
│
├── Navigation Callback Handler
│   └── navigation_handler()
│       └── Handles inline buttons from the /status command
│
└── Main
    ├── main()
    │   ├── Build ApplicationBuilder
    │   ├── Add all handlers
    │   └── Start polling
    └── __main__
```

## Data Flow Diagrams

### Guided Workflow after `/status`

```
User sends /status
    ↓
bot.status()
    ├─ await get_location_status()
    └─ await get_nodes_in_location()
    ↓
analyze_location_health()
    ↓
Bot sends formatted health report message
    ↓
Bot sends a *second* message:
"What would you like to do next?"
    ├─ [ Get Node Details ] (button)
    ├─ [ List WiFi Networks ] (button)
    └─ [ Change Location ] (button)
    ↓
User clicks a button (e.g., "Get Node Details")
    ↓
bot.navigation_handler()
    ├─ Deletes the button message for a clean UI
    └─ Calls the corresponding command handler (e.g., bot.nodes())
    ↓
User sees the detailed report
```
