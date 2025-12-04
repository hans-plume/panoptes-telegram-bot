# Plume Bot - Code Architecture

**Version:** 1.0  
**Last Updated:** December 2024

## Module Structure

```
panoptes_bot.py
├── Imports & Configuration
│   ├── telegram (bot framework)
│   ├── plume_api_client imports
│   ├── src/handlers imports
│   └── ConversationHandler (setup, locations flows)
│
├── Configuration
│   ├── TELEGRAM_BOT_TOKEN (from env)
│   ├── Logging setup
│   └── Conversation state constants
│
├── Conversation States
│   ├── (ASK_AUTH_HEADER, ASK_PARTNER_ID) - 2-step OAuth
│   └── (ASK_CUSTOMER_ID, SELECT_LOCATION) - Location selection
│
├── Error Handler
│   └── error_handler() - Global error handling
│
├── Helper Functions
│   ├── get_reply_source()
│   ├── format_speed_test()
│   └── format_pod_details()
│
├── Command Handlers
│   ├── start() - Welcome message
│   ├── status() - Main health report with action buttons
│   ├── wan_command() - WAN consumption report
│   ├── nodes() - Detailed pod info
│   └── wifi() - WiFi SSID list
│
├── Navigation Callback Handler
│   └── navigation_handler()
│       └── Handles inline buttons from /status command
│
├── Conversation Handlers
│   ├── Setup Conversation (/setup) - 2-step OAuth
│   │   ├── setup_start()
│   │   ├── ask_partner_id()
│   │   ├── confirm_auth()
│   │   └── cancel_setup()
│   └── Locations Conversation (/locations)
│       ├── locations_start()
│       ├── customer_id_provided()
│       ├── location_selected()
│       └── locations_cancel()
│
└── Main
    ├── main()
    │   ├── Build ApplicationBuilder
    │   ├── Add all handlers
    │   ├── Add stats_command handler
    │   └── Start polling
    └── __main__

plume_api_client.py
├── Configuration & Logging
│   ├── PLUME_API_BASE (from env)
│   ├── PLUME_REPORTS_BASE (from env)
│   ├── PLUME_SSO_URL
│   └── PLUME_TIMEOUT
│
├── Exceptions
│   └── PlumeAPIError
│
├── Authentication Management
│   ├── user_auth{} - Token storage
│   ├── set_user_auth(user_id, config)
│   ├── get_user_auth(user_id)
│   ├── is_oauth_token_valid(user_id)
│   └── get_oauth_token(auth_config)
│
├── Plume API Client
│   └── plume_request()
│       ├── Manages token validation and refresh
│       ├── Supports API and Reports endpoints
│       └── Makes all authenticated API calls
│
├── API Wrapper Functions
│   ├── get_customers()
│   ├── get_locations_for_customer()
│   ├── get_nodes_in_location()
│   ├── get_location_status()
│   ├── get_wifi_networks()
│   └── get_wan_stats()
│
└── Service Health Analysis
    ├── analyze_location_health()
    │   └── Generates health report dictionary
    ├── analyze_wan_stats()
    │   └── Generates consumption analytics
    └── format_wan_analysis()
        └── Formats WAN data into markdown report

src/handlers/location_stats.py
├── TIME_RANGES configuration
├── create_time_range_keyboard()
├── fetch_and_format_stats()
├── stats_command() - /stats handler
└── stats_time_range_callback() - Time range buttons

src/api/online_stats.py
└── get_location_online_stats()

src/utils/
├── stats_processor.py
│   └── process_online_stats()
└── stats_formatter.py
    └── format_online_stats_message()
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
    ├─ [ WAN Consumption Report ] (button)
    ├─ [ Online Stats Report ] (button)
    ├─ [ Get Node Details ] (button)
    ├─ [ List WiFi Networks ] (button)
    └─ [ Change Location ] (button)
    ↓
User clicks a button (e.g., "WAN Consumption Report")
    ↓
bot.navigation_handler()
    ├─ Deletes the button message for a clean UI
    └─ Calls the corresponding command handler (e.g., bot.wan_command())
    ↓
User sees the detailed report
```

### OAuth Setup Flow (2-Step)

```
User sends /setup
    ↓
bot.setup_start()
    ↓
Bot asks: "Please provide your Plume authorization header"
    ↓
User provides: "Basic abc123..."
    ↓
bot.ask_partner_id()
    ↓
Bot asks: "Please provide your Plume Partner ID"
    ↓
User provides: "eb0af9d0a7ab946dcb3b8ef5"
    ↓
bot.confirm_auth()
    ├─ set_user_auth() stores credentials
    ├─ get_oauth_token() tests connection
    └─ If success: "✅ API connection is working! Run /locations"
    ↓
User sends /locations
    ↓
bot.locations_start()
    ↓
... (Location selection flow)
```

### /stats Command Flow

```
User sends /stats
    ↓
stats_command() (src/handlers/location_stats.py)
    ├─ Get location_name from API
    └─ fetch_and_format_stats(granularity="days", limit=7)
        ├─ get_location_online_stats()
        ├─ process_online_stats()
        └─ format_online_stats_message()
    ↓
Bot sends stats message + time range buttons:
    [ 3 Hrs ] [ 24 Hrs ] [ 7 Days ]
    ↓
User clicks [ 24 Hrs ]
    ↓
stats_time_range_callback()
    └─ fetch_and_format_stats(granularity="days", limit=1)
    ↓
Bot updates message with 24-hour stats
```

## Command Summary

| Command | Handler | Location | Description |
|---------|---------|----------|-------------|
| `/start` | `start()` | panoptes_bot.py | Welcome, guides next step |
| `/setup` | `setup_start()` | panoptes_bot.py | 2-step OAuth setup |
| `/locations` | `locations_start()` | panoptes_bot.py | Select customer/location |
| `/status` | `status()` | panoptes_bot.py | Health dashboard + actions |
| `/wan` | `wan_command()` | panoptes_bot.py | WAN consumption report |
| `/stats` | `stats_command()` | src/handlers/location_stats.py | Online stats with time ranges |
| `/nodes` | `nodes()` | panoptes_bot.py | Pod details |
| `/wifi` | `wifi()` | panoptes_bot.py | WiFi network list |

## API Functions Summary

| Function | Module | Purpose |
|----------|--------|---------|
| `get_oauth_token()` | plume_api_client.py | Exchange credentials for token |
| `set_user_auth()` | plume_api_client.py | Store user's OAuth config |
| `is_oauth_token_valid()` | plume_api_client.py | Check token validity |
| `plume_request()` | plume_api_client.py | Generic authenticated API call |
| `get_customers()` | plume_api_client.py | Get partner's customers |
| `get_locations_for_customer()` | plume_api_client.py | Get customer's locations |
| `get_nodes_in_location()` | plume_api_client.py | Get pods in location |
| `get_location_status()` | plume_api_client.py | Get location health info |
| `get_wifi_networks()` | plume_api_client.py | Get WiFi SSIDs |
| `get_wan_stats()` | plume_api_client.py | Get WAN consumption data |
| `analyze_location_health()` | plume_api_client.py | Generate health report |
| `analyze_wan_stats()` | plume_api_client.py | Analyze WAN stats |
| `format_wan_analysis()` | plume_api_client.py | Format WAN report |
| `get_location_online_stats()` | src/api/online_stats.py | Get online stats |
