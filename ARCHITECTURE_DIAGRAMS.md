# Modularization: Visual Architecture

**Version:** 1.0  
**Last Updated:** December 2024

## High-Level Package Structure

```
panoptes-telegram-bot/
│
├── plume_api_client.py (~490 lines)
│   ├── OAuth Management
│   ├── API Wrappers  
│   ├── Health Analysis (location + WAN)
│   └── Error Handling
│
├── panoptes_bot.py (~400 lines)
│   ├── Telegram Bot
│   ├── Command Handlers
│   ├── Formatters
│   └── Conversations (setup, locations)
│
├── src/
│   ├── api/
│   │   └── online_stats.py (Online stats API)
│   ├── handlers/
│   │   └── location_stats.py (/stats command)
│   └── utils/
│       ├── stats_processor.py
│       └── stats_formatter.py
│
├── __init__.py (~40 lines)
│   └── Public API
│
└── Documentation/
    ├── ARCHITECTURE_DIAGRAMS.md
    ├── BOT_ARCHITECTURE.md
    ├── BOT_IMPLEMENTATION_SUMMARY.md
    ├── BOT_OAUTH_SETUP_GUIDE.md
    ├── BOT_QUICK_REFERENCE.md
    ├── QUICK_REFERENCE.md
    ├── README.md
    └── WAN_CONSUMPTION_GUIDE.md
```

---

## Data Flow Architecture

### OAuth Flow (2-Step Process)
```
┌─────────────────────────────────────────────────────────────────┐
│ Telegram User                                                   │
└───────────────────────┬──────────────────────────────────────────┘
                        │ /setup
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ panoptes_bot.py                                                 │
│ ┌──────────────────────────────────────────────────────────────┐│
│ │ OAuth Conversation Handler (2 steps)                         ││
│ │ ├─ setup_start() → asks for Auth Header                      ││
│ │ ├─ ask_partner_id() → asks for Partner ID                    ││
│ │ └─ confirm_auth() → tests connection                         ││
│ └──────────┬───────────────────────────────────────────────────┘│
└────────────┼──────────────────────────────────────────────────────┘
             │ Call get_oauth_token(auth_config)
             ↓
┌─────────────────────────────────────────────────────────────────┐
│ plume_api_client.py                                             │
│ ┌──────────────────────────────────────────────────────────────┐│
│ │ get_oauth_token(auth_config)                                 ││
│ │ ├─ Validate credentials                                      ││
│ │ ├─ Build OAuth request                                       ││
│ │ └─ Call Plume SSO endpoint                                   ││
│ └──────────┬───────────────────────────────────────────────────┘│
└────────────┼──────────────────────────────────────────────────────┘
             │ POST https://external.sso.plume.com/oauth2/.../token
             ↓
         Plume OAuth Server
             │ Return: {access_token, expires_in}
             ↓
┌────────────┴───────────────────────────────────────────────────────┐
│ plume_api_client.py                                                │
│ ├─ Calculate token expiry (expires_in - 60 seconds)                │
│ └─ Store in user_auth dictionary                                   │
└────────────┬──────────────────────────────────────────────────────┘
             │ Return success
             ↓
         User authenticated! ✅ → Suggests /locations
```

### Command Execution Flow

```
User: /status (with location already selected)
            │
            ↓
┌──────────────────────────────────────────────────────┐
│ panoptes_bot.py - status()                           │
│                                                      │
│ Calls API functions:                                 │
│  ├─ get_location_status()                           │
│  └─ get_nodes_in_location()                         │
└────────────┬─────────────────────────────────────────┘
             │
             ↓
   plume_api_client.py (async calls)
             │
             ↓
    Plume Cloud API
    Multiple endpoints
             │
             ↓
    Returns: location_data, nodes
             │
             ↓
        ┌───────────────────────────────────────────┐
        │ analyze_location_health()                 │
        │ (plume_api_client.py)                     │
        │                                           │
        │ Combines all data:                        │
        │ • Online status                           │
        │ • Issues (disconnected pods)              │
        │ • Warnings (health alerts)                │
        │ • Summary (🟢🟡🟠🔴)                       │
        └───────────┬─────────────────────────────┘
                    │
                    ↓ Returns: health dictionary
        ┌───────────────────────────────────────────┐
        │ format_pod_details() + format_speed_test()│
        │ (panoptes_bot.py)                         │
        │                                           │
        │ Converts to Telegram markdown:            │
        │ • Bold status                             │
        │ • Emoji indicators                        │
        │ • Lists of issues                         │
        └───────────┬─────────────────────────────┘
                    │
                    ↓
            Telegram response to user
            + Inline keyboard with next actions
```

### WAN Consumption Flow

```
User: /wan
            │
            ↓
┌──────────────────────────────────────────────────────┐
│ panoptes_bot.py - wan_command()                      │
└────────────┬─────────────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────────────────────┐
│ plume_api_client.py                                  │
│  └─ get_wan_stats() (use_reports_api=True)          │
└────────────┬─────────────────────────────────────────┘
             │
             ↓
    Plume Reports API
    /Customers/{id}/locations/{id}/wanStats
             │
             ↓
    Returns: {fifteenMins: [...]}
             │
             ↓
        ┌───────────────────────────────────────────┐
        │ analyze_wan_stats()                       │
        │ (plume_api_client.py)                     │
        │                                           │
        │ Calculates:                               │
        │ • Peak RX/TX with timestamps              │
        │ • Average usage                           │
        │ • 95th percentile                         │
        │ • Total data transferred                  │
        │ • Peak activity windows                   │
        └───────────┬─────────────────────────────┘
                    │
                    ↓
        ┌───────────────────────────────────────────┐
        │ format_wan_analysis()                     │
        │ (plume_api_client.py)                     │
        │                                           │
        │ Formats into Telegram markdown report     │
        └───────────┬─────────────────────────────┘
                    │
                    ↓
            Telegram response to user
```

### Online Stats Flow (/stats command)

```
User: /stats
            │
            ↓
┌──────────────────────────────────────────────────────┐
│ src/handlers/location_stats.py - stats_command()     │
└────────────┬─────────────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────────────────────┐
│ src/api/online_stats.py                              │
│  └─ get_location_online_stats()                      │
└────────────┬─────────────────────────────────────────┘
             │
             ↓
    Plume Reports API
    /Customers/{id}/locations/{id}/onlineStats
             │
             ↓
    Returns: {statsDateRange, locationState}
             │
             ↓
        ┌───────────────────────────────────────────┐
        │ src/utils/stats_processor.py              │
        │ process_online_stats()                    │
        └───────────┬─────────────────────────────┘
                    │
                    ↓
        ┌───────────────────────────────────────────┐
        │ src/utils/stats_formatter.py              │
        │ format_online_stats_message()             │
        └───────────┬─────────────────────────────┘
                    │
                    ↓
            Telegram response + Time range buttons
            [3 Hrs] [24 Hrs] [7 Days]
```

---

## Module Interaction Diagram

```
                    ┌──────────────────┐
                    │  Telegram User   │
                    └────────┬─────────┘
                             │
                             │ /command
                             ↓
          ┌──────────────────────────────────────┐
          │      panoptes_bot.py                 │
          │  ┌─────────────────────────────────┐ │
          │  │ Handlers & Formatters           │ │
          │  │                                 │ │
          │  │ • Command routing               │ │
          │  │ • User interactions             │ │
          │  │ • Telegram formatting           │ │
          │  │ • Setup conversation (2-step)   │ │
          │  │ • Location conversation         │ │
          │  │                                 │ │
          │  └──────┬──────────────────────────┘ │
          │         │ Imports & calls            │
          │         ↓                            │
          │  ┌─────────────────────────────────┐ │
          │  │ Imports from plume_api_client:  │ │
          │  │ • set_user_auth()               │ │
          │  │ • is_oauth_token_valid()        │ │
          │  │ • get_oauth_token()             │ │
          │  │ • get_locations_for_customer()  │ │
          │  │ • get_nodes_in_location()       │ │
          │  │ • get_location_status()         │ │
          │  │ • get_wifi_networks()           │ │
          │  │ • get_wan_stats()               │ │
          │  │ • analyze_location_health()     │ │
          │  │ • analyze_wan_stats()           │ │
          │  │ • format_wan_analysis()         │ │
          │  │ • PlumeAPIError                 │ │
          │  └─────────────────────────────────┘ │
          └──────────┬──────────────────────────┘
                     │
                     │ From local import
                     ↓
       ┌────────────────────────────────────────┐
       │  plume_api_client.py                   │
       │  ┌─────────────────────────────────────┤
       │  │ Layer 1: Authentication             │
       │  │ ├─ get_oauth_token()                │
       │  │ ├─ is_oauth_token_valid()           │
       │  │ ├─ set_user_auth()                  │
       │  │ └─ get_user_auth()                  │
       │  └─────────────────────────────────────┤
       │  │ Layer 2: API Wrapper                │
       │  │ ├─ plume_request() [base]           │
       │  │ ├─ Error handling (PlumeAPIError)   │
       │  │ └─ Token injection/refresh          │
       │  └─────────────────────────────────────┤
       │  │ Layer 3: Endpoints                  │
       │  │ ├─ get_customers()                  │
       │  │ ├─ get_locations_for_customer()     │
       │  │ ├─ get_nodes_in_location()          │
       │  │ ├─ get_location_status()            │
       │  │ ├─ get_wifi_networks()              │
       │  │ └─ get_wan_stats()                  │
       │  └─────────────────────────────────────┤
       │  │ Layer 4: Analysis                   │
       │  │ ├─ analyze_location_health()        │
       │  │ ├─ analyze_wan_stats()              │
       │  │ └─ format_wan_analysis()            │
       │  └─────────────────────────────────────┤
       └──────────┬─────────────────────────────┘
                  │ HTTP calls
                  ↓
          ┌──────────────────┐
          │ Plume Cloud API  │
          │ /api/Customers/..│
          │ /reports/...     │
          └──────────────────┘
```

---

## File Size Comparison

### Before Modularization
```
panoptes_bot.py
████████████████████████████████████████████ ~1000 lines

Everything mixed:
- Auth (~150 lines)
- API wrappers (~200 lines)
- Health analysis (~100 lines)
- Handlers (~350 lines)
- Formatters (~200 lines)
```

### After Modularization (v1.0)
```
plume_api_client.py
█████████████████████ ~490 lines (API layer)

panoptes_bot.py
████████████████ ~400 lines (Bot handlers)

src/handlers/location_stats.py
████ ~215 lines (Stats command)

src/api/online_stats.py
██ ~60 lines (Online stats API)

src/utils/stats_*.py
███ ~100 lines (Stats processing)

Result: Focused modules, easier to navigate and test
```

---

## Dependency Graph

### Modularized Architecture
```
plume_api_client.py (Pure API layer)
├── httpx         ← For API calls only
├── logging       ← For logs
├── datetime      ← For tokens
└── os            ← For env vars

↑ Can be used independently
│ No Telegram dependency

panoptes_bot.py (Bot layer)
├── telegram      ← For bot only
├── logging       ← For logs
└── plume_api_client → Import API functions

src/handlers/location_stats.py
├── telegram      ← For bot handlers
├── plume_api_client → Import API functions
└── src/api/online_stats → Import stats API

Result: Loose coupling, high cohesion
```

---

## Testability

### Easy to Test
```
test_plume_api_client.py
├─ Test OAuth logic
├─ Test API wrappers
├─ Test health analysis
├─ Test WAN analysis
└─ Unit tests (no Telegram needed) ✓

test_panoptes_bot.py
├─ Test handlers
├─ Test formatters
└─ Integration tests

test_location_stats.py
├─ Test stats processing
├─ Test stats formatting
└─ Unit tests
```

---

## Scalability: Adding New Features

### Adding a New Command
```
1. If API call needed:
   Edit plume_api_client.py → Add new API wrapper

2. Add command handler:
   Edit panoptes_bot.py → Add handler function
   Or create new handler in src/handlers/

3. Register handler in main():
   application.add_handler(CommandHandler("new", new_handler))

4. Review: Isolated to specific files
5. Risk: Changes isolated to handler code
```

---

## Environment & Dependencies

### Installation
```bash
pip install -r requirements.txt

# Dependencies:
# - python-telegram-bot[job-queue]
# - httpx[http2]
# - pydantic
# - pytz
# - python-dotenv
```

### Environment Variables
```bash
# Required
export TELEGRAM_BOT_TOKEN="123456:ABC..."

# Optional (have defaults)
export PLUME_API_BASE="https://piranha-gamma.prod.us-west-2.aws.plumenet.io/api/"
export PLUME_REPORTS_BASE="https://piranha-gamma.prod.us-west-2.aws.plumenet.io/reports/"
```

---

## Performance Impact

### No Regression
- ✅ Same async/await patterns
- ✅ Same API calls
- ✅ Same health analysis
- ✅ Same token management
- ✅ Same error handling

### Improvements in v1.0
- ✅ WAN consumption analytics
- ✅ Online stats with time ranges
- ✅ Inline navigation buttons
- ✅ Better user guidance

---

## Summary

**v1.0 Architecture:**
- ✅ Modular design: API layer + Bot layer
- ✅ Easy to test each layer independently
- ✅ Reusable API client
- ✅ Clear separation of concerns
- ✅ Easy to maintain and extend

**Key Modules:**
- `plume_api_client.py` – All Plume API interactions
- `panoptes_bot.py` – Telegram bot and handlers
- `src/` – Extended functionality (stats)

---

For detailed information, see:
- `README.md` – Getting started guide
- `QUICK_REFERENCE.md` – Developer quick reference
- `BOT_ARCHITECTURE.md` – Bot-specific architecture
- `WAN_CONSUMPTION_GUIDE.md` – WAN report explanation
