# Modularization: Visual Architecture

## High-Level Package Structure

```
plume-cloud-bot/
│
├── plume_api_client.py (461 lines)
│   ├── OAuth Management
│   ├── API Wrappers  
│   ├── Health Analysis
│   └── Error Handling
│
├── panoptes_bot.py (676 lines)
│   ├── Telegram Bot
│   ├── Command Handlers
│   ├── Formatters
│   └── Conversations
│
├── __init__.py (40 lines)
│   └── Public API
│
└── Documentation/
    ├── MODULARIZATION_GUIDE.md
    ├── MODULARIZATION_COMPLETE.md
    ├── BOT_OAUTH_SETUP_GUIDE.md
    ├── BOT_QUICK_REFERENCE.md
    ├── BOT_ARCHITECTURE.md
    └── BOT_IMPLEMENTATION_SUMMARY.md
```

---

## Data Flow Architecture

### OAuth Flow
```
┌─────────────────────────────────────────────────────────────────┐
│ Telegram User                                                   │
└───────────────────────┬──────────────────────────────────────────┘
                        │ /auth
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ panoptes_bot.py                                                 │
│ ┌──────────────────────────────────────────────────────────────┐│
│ │ OAuth Conversation Handler                                   ││
│ │ ├─ receive_sso_url()                                         ││
│ │ ├─ receive_auth_header()                                     ││
│ │ ├─ receive_partner_id()                                      ││
│ │ ├─ receive_api_base()                                        ││
│ │ └─ confirm_auth()                                            ││
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
             │ POST https://...sso.../oauth2/.../token
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
         User authenticated! ✅
```

### Command Execution Flow

```
User: /health <customerId> <locationId>
            │
            ↓
┌──────────────────────────────────────────────────────┐
│ panoptes_bot.py - handle_health_command()            │
│                                                      │
│ Calls 5 API functions in parallel:                  │
│  ├─ get_location_status()                           │
│  ├─ get_service_level()                             │
│  ├─ get_nodes_in_location()                         │
│  ├─ get_connected_devices()                         │
│  └─ get_qoe_stats()                                 │
└────────────┬─────────────────────────────────────────┘
             │
      ┌──────┴──────┬──────────┬─────────┬──────────┐
      ↓             ↓          ↓         ↓          ↓
   plume_api_client (all in parallel with async/await)
      │             │          │         │          │
      └──────┬──────┴──────────┴─────────┴──────────┘
             │
             ↓
    Plume Cloud API
    Multiple endpoints
             │
      ┌──────┴──────┬──────────┬─────────┬──────────┐
      ↓             ↓          ↓         ↓          ↓
    Returns: location, service_level, nodes, devices, qoe
             │             │          │         │          │
             └──────┬──────┴──────────┴─────────┴──────────┘
                    │
                    ↓
        ┌───────────────────────────────────────────┐
        │ analyze_location_health()                 │
        │ (plume_api_client.py)                     │
        │                                           │
        │ Combines all data:                        │
        │ • Online status                           │
        │ • Issues (disconnected pods)              │
        │ • Warnings (disconnected devices)         │
        │ • Poor QoE traffic                        │
        │ • Summary (🟢🟡🟠🔴)                   │
        └───────────┬─────────────────────────────┘
                    │
                    ↓ Returns: health dictionary
        ┌───────────────────────────────────────────┐
        │ format_health_report()                    │
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
          │  │ • OAuth conversation            │ │
          │  │                                 │ │
          │  └──────┬──────────────────────────┘ │
          │         │ Imports & calls            │
          │         ↓                            │
          │  ┌─────────────────────────────────┐ │
          │  │ Imports from plume_api_client:  │ │
          │  │ • get_oauth_token()             │ │
          │  │ • get_nodes_in_location()       │ │
          │  │ • analyze_location_health()     │ │
          │  │ • ... (15 total)                │ │
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
       │  │ └─ set_user_auth()                  │
       │  └─────────────────────────────────────┤
       │  │ Layer 2: API Wrapper                │
       │  │ ├─ plume_request() [base]           │
       │  │ ├─ Error handling                   │
       │  │ └─ Token injection                  │
       │  └─────────────────────────────────────┤
       │  │ Layer 3: Endpoints                  │
       │  │ ├─ get_nodes_in_location()          │
       │  │ ├─ get_connected_devices()          │
       │  │ ├─ get_service_level()              │
       │  │ └─ get_qoe_stats() (7 total)        │
       │  └─────────────────────────────────────┤
       │  │ Layer 4: Analysis                   │
       │  │ └─ analyze_location_health()        │
       │  └─────────────────────────────────────┤
       └──────────┬─────────────────────────────┘
                  │ HTTP calls
                  ↓
          ┌──────────────────┐
          │ Plume Cloud API  │
          │ /api/Customers/..
          │ /api/partners/...
          └──────────────────┘
```

---

## File Size Comparison

### Before Modularization
```
panoptes_bot.py
████████████████████████████████████████████ 1006 lines

Everything mixed:
- Auth (150 lines)
- API wrappers (200 lines)
- Health analysis (100 lines)
- Handlers (350 lines)
- Formatters (206 lines)
```

### After Modularization
```
plume_api_client.py
█████████████████████ 461 lines (API layer)

panoptes_bot.py
██████████████████████████ 676 lines (Handlers + Formatters)

__init__.py
██ 40 lines (Package interface)

Result: Focused modules, easier to navigate and test
```

---

## Dependency Graph

### Before (Monolithic)
```
panoptes_bot.py
├── httpx         ← For API calls
├── telegram      ← For bot
├── logging       ← For logs
├── datetime      ← For tokens
└── os            ← For env vars

Everything in one file = high coupling
```

### After (Modularized)
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
└── plume_api_client → Weak dependency

Result: Loose coupling, high cohesion
```

---

## Testability Comparison

### Before (Hard to Test)
```
test_panoptes_bot.py
├─ Need to mock httpx
├─ Need to mock telegram
├─ Need to mock logging
├─ Need to mock datetime
└─ All tests are integration tests
   (Can't test API logic without Telegram context)
```

### After (Easy to Test)
```
test_plume_api_client.py
├─ Test OAuth logic
├─ Test API wrappers
├─ Test health analysis
└─ Unit tests (no Telegram needed) ✓

test_panoptes_bot.py
├─ Test handlers
├─ Test formatters
└─ Integration tests
```

---

## Scalability: Adding New Features

### Before: Adding New Command
```
1. Edit panoptes_bot.py
2. Add handler function → Navigate 1000+ lines
3. Risk: Breaking API logic while modifying handler code
4. Review: 1000+ lines in one diff
```

### After: Adding New Command
```
1. Edit panoptes_bot.py (only Telegram logic)
2. Add handler → Navigate 676 lines (cleaner!)
3. Import from plume_api_client if needed
4. Review: ~50-100 lines in diff
5. Risk: Isolated to handler code
```

---

## Environment & Dependencies

### Installation
```bash
pip install python-telegram-bot httpx

# Only these 2 dependencies needed
# plume_api_client: httpx, logging, os, datetime (stdlib)
# panoptes_bot: telegram (external), logging, os (stdlib)
```

### Environment Variables
```bash
# Required
export TELEGRAM_BOT_TOKEN="123456:ABC..."

# Optional
export PLUME_API_BASE="https://api.plume.com"
```

---

## Performance Impact

### No Regression
- ✅ Same async/await patterns
- ✅ Same API calls
- ✅ Same health analysis
- ✅ Same token management
- ✅ Same error handling

### Potential Improvements (Future)
- Add Redis caching (both modules benefit)
- Add connection pooling (httpx)
- Add rate limiting (both modules benefit)

---

## Summary

**Before:** 1 monolithic file (1006 lines)
- ❌ Hard to test
- ❌ Can't reuse API
- ❌ Mixed concerns
- ❌ Difficult to maintain

**After:** 2 focused modules (1137 lines with docs)
- ✅ Easy to test
- ✅ Reusable API
- ✅ Clear separation
- ✅ Easy to maintain

**Code Quality:** ⬆️ Improved  
**Functionality:** ↔️ Unchanged  
**Flexibility:** ⬆️ Improved  
**Maintainability:** ⬆️ Improved  

---

For detailed information, see:
- `MODULARIZATION_GUIDE.md` - Complete architecture guide
- `MODULARIZATION_COMPLETE.md` - Metrics and verification
- `plume_api_client.py` - API implementation
- `panoptes_bot.py` - Bot implementation
