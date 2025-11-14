# Panoptes Telegram Bot

Real-time Plume Cloud network monitoring via Telegram with OAuth 2.0 authentication.

## Features

- 🔐 **OAuth 2.0 Authentication** - Secure Client Credentials flow
- 📊 **Network Monitoring** - Real-time health, nodes, devices, QoE stats
- 📱 **Device Tracking** - Connected devices and WiFi pod status
- 🟢 **Health Indicators** - Visual status with emoji (🟢🟡🟠🔴)
- 🔄 **Auto Token Refresh** - Automatic token renewal 60 seconds before expiry
- 📡 **Multiple Endpoints** - Location, devices, service health, QoE, connectivity
- ⚠️ **Error Handling** - Graceful error messages and automatic recovery

## Quick Start

### Prerequisites

- Python 3.8+
- Telegram Bot (get from @BotFather on Telegram)
- Plume Cloud API credentials

### Installation

1. Clone the repository:
```bash
git clone https://github.com/hans-plume/panoptes-telegram-bot.git
cd panoptes-telegram-bot
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
echo "TELEGRAM_BOT_TOKEN=your_token_here" >> .env
```

5. Run the bot:
```bash
python panoptes_bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome & command list |
| `/help` | Show help message |
| `/auth` | OAuth 2.0 setup (4 steps) |
| `/health` | Network health check |
| `/nodes` | List connected nodes |
| `/devices` | List connected devices |
| `/wifi` | WiFi pod status |
| `/status` | Full network report |

## OAuth Setup

When you run `/auth`, the bot will guide you through 4 steps:

1. **SSO URL** - OAuth endpoint (e.g., `https://external.sso.plume.com/oauth2/{auth-id}/v1/token`)
2. **Authorization Header** - Bearer token format
3. **Partner ID** - Numeric ID
4. **API Base URL** - API endpoint (e.g., `https://api.plume.com/cloud/v1`)

## Architecture

- **plume_api_client.py** - Pure API layer (OAuth, endpoints, health analysis)
- **panoptes_bot.py** - Telegram handlers (commands, formatters, conversation)
- **__init__.py** - Package interface

## Documentation

See `DOCUMENTATION_INDEX.md` for complete guide navigation.

## License

MIT
