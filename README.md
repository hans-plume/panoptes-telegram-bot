# Panoptes Telegram Bot - Plume Cloud Monitoring

**Version:** 1.0  
**Last Updated:** December 2024  
**Author:** Hans V.

A production-ready Telegram bot for real-time monitoring of Plume Cloud networks, featuring a complete OAuth 2.0 authentication flow and a guided user experience.

---

## Features

- **Guided User Workflow**: The bot intelligently suggests the next logical command, creating a seamless user experience from setup to detailed analysis.
- **Full OAuth 2.0 Authentication**: A secure, 2-step conversation handler (`/setup`) for one-time API credential configuration.
- **Automatic Token Management**: Automatically obtains and refreshes OAuth tokens, ensuring uninterrupted API access.
- **Enhanced Network Status (`/status`)**: A comprehensive overview of location health, including:
    - Overall summary (Online, Offline, Degraded Service).
    - Detailed per-pod status (connection, health, backhaul type, and alerts).
    - Latest ISP speed test results (download, upload, latency).
    - Total number of connected devices.
    - Inline buttons for quick navigation to other reports.
- **WAN Consumption Report (`/wan`)**: Detailed bandwidth consumption analytics including:
    - Peak capacity usage (RX/TX) with timestamps
    - Average and 95th percentile bandwidth metrics
    - Total data transferred (download/upload)
    - Peak activity window detection
    - Data quality assessment
- **Online Stats Report (`/stats`)**: Connection status history with selectable time ranges:
    - 3-hour, 24-hour, and 7-day views
    - Location uptime and connectivity trends
    - Interactive time range selection buttons
- **Detailed Node Information (`/nodes`)**: Get technical details for each pod, including model, firmware version, MAC, and IP address.
- **WiFi Network Listing (`/wifi`)**: Display all configured SSIDs for the location, including their security mode.
- **Location-Centric Workflow**: A dedicated conversation (`/locations`) to select a customer and location, which is then remembered for subsequent commands.
- **Modular and Asynchronous Codebase**: Built with `python-telegram-bot` and `httpx` for a scalable, high-performance, and maintainable architecture. The codebase is split into:
    - `plume_api_client.py` – API layer (OAuth, API wrappers, health analysis)
    - `panoptes_bot.py` – Bot layer (command handlers, formatters, conversations)

---

## Command Reference

### Setup and Navigation
| Command | Description |
|---|---|
| `/start` | Initializes the bot. Guides to `/setup` or `/locations`. |
| `/setup` | Starts the guided, 2-step OAuth 2.0 setup conversation. |
| `/locations`| Starts the conversation to select a customer and location to monitor. |

### Monitoring Commands
*Note: A location must be selected with `/locations` before using these commands.*

| Command | Description |
|---|---|
| `/status` | Displays the main, enhanced health report for the selected location and suggests next steps. |
| `/wan` | Shows WAN consumption analytics including peak usage, averages, and data transfer totals. |
| `/stats` | Shows connection status history with selectable time ranges (3h, 24h, 7d). |
| `/nodes` | Shows detailed technical information for every pod in the location. |
| `/wifi` | Lists all configured WiFi SSIDs and their security settings for the location. |

---

## Getting Started - 'for contanier deployment'

### Prerequisites
- Python 3.8+ (or Docker)
- A Telegram Bot Token
- Plume Cloud API Credentials (Authorization Header and Partner ID)

### Installation (Standard)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/hans-plume/panoptes-telegram-bot.git
    cd panoptes-telegram-bot
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the root directory and add your Telegram Bot token:
    ```
    TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234567890"
    ```

### Running the Bot

Execute the main bot script:
```bash
python -m panoptes_bot
```

### Running with Docker

Docker provides a consistent, containerized environment for running the bot.

#### Using Docker Compose (Recommended)

1.  **Build and start the bot:**
    ```bash
    docker compose up -d
    ```

2.  **View logs:**
    ```bash
    docker compose logs -f
    ```

3.  **Stop the bot:**
    ```bash
    docker compose down
    ```

#### Using Docker Directly

1.  **Build the image:**
    ```bash
    docker build -t panoptes-telegram-bot .
    ```

2.  **Run the container:**
    ```bash
    docker run -d --name panoptes-bot --env-file .env panoptes-telegram-bot
    ```

3.  **View logs:**
    ```bash
    docker logs -f panoptes-bot
    ```

4.  **Stop the container:**
    ```bash
    docker stop panoptes-bot && docker rm panoptes-bot
    ```

### First-Time Use

1.  **Start a chat** with your bot in Telegram and send `/start`.
2.  The bot will prompt you to run `/setup`.
3.  Follow the 2-step OAuth setup:
    - **Step 1**: Provide your Plume Authorization Header
    - **Step 2**: Provide your Plume Partner ID
4.  Once setup is complete, the bot will suggest you run `/locations`.
5.  Use `/locations` to select the customer and network location you wish to monitor.
6.  Run `/status` to see your first network health report.
7.  After `/status`, the bot displays inline buttons for quick access to:
    - **WAN Consumption Report** (`/wan`)
    - **Online Stats Report** (`/stats`)
    - **Node Details** (`/nodes`)
    - **WiFi Networks** (`/wifi`)
    - **Change Location** (`/locations`)

---

## Architecture

The bot uses a modular architecture with clear separation of concerns:

```
panoptes-telegram-bot/
├── plume_api_client.py    # API layer: OAuth, API wrappers, health analysis
├── panoptes_bot.py        # Bot layer: handlers, formatters, conversations
├── src/
│   ├── api/               # Additional API endpoints (online stats)
│   ├── handlers/          # Additional command handlers (stats)
│   └── utils/             # Utilities (stats processor, formatter)
└── tests/                 # Test suite
```

See `ARCHITECTURE_DIAGRAMS.md` and `BOT_ARCHITECTURE.md` for detailed architecture documentation.
