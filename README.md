# Panoptes Telegram Bot - Plume Cloud Monitoring

**Version:** 0.9.0  
**Author:** Hans V.

A production-ready Telegram bot for real-time monitoring of Plume Cloud networks, featuring a complete OAuth 2.0 authentication flow and a guided user experience.

---

## Features

- **Guided User Workflow**: The bot intelligently suggests the next logical command, creating a seamless user experience from setup to detailed analysis.
- **Full OAuth 2.0 Authentication**: A secure, multi-step conversation handler (`/setup`) for one-time API credential configuration.
- **Automatic Token Management**: Automatically obtains and refreshes OAuth tokens, ensuring uninterrupted API access.
- **Enhanced Network Status (`/status`)**: A comprehensive overview of location health, including:
    - Overall summary (Online, Offline, Degraded Service).
    - Detailed per-pod status (connection, health, backhaul type, and alerts).
    - Latest ISP speed test results (download, upload, latency).
    - Total number of connected devices.
- **Detailed Node Information (`/nodes`)**: Get technical details for each pod, including model, firmware version, MAC, and IP address.
- **WiFi Network Listing (`/wifi`)**: Display all configured SSIDs for the location, including their security mode.
- **Location-Centric Workflow**: A dedicated conversation (`/locations`) to select a customer and location, which is then remembered for subsequent commands.
- **Modular and Asynchronous Codebase**: Built with `python-telegram-bot` and `httpx` for a scalable, high-performance, and maintainable architecture.

---

## Command Reference

### Setup and Navigation
| Command | Description |
|---|---|
| `/start` | Initializes the bot. Guides to `/setup` or `/locations`. |
| `/setup` | Starts the guided, one-time OAuth 2.0 setup conversation. |
| `/locations`| Starts the conversation to select a customer and location to monitor. |

### Monitoring Commands
*Note: A location must be selected with `/locations` before using these commands.*

| Command | Description |
|---|---|
| `/status` | Displays the main, enhanced health report for the selected location and suggests next steps. |
| `/nodes` | Shows detailed technical information for every pod in the location. |
| `/wifi` | Lists all configured WiFi SSIDs and their security settings for the location. |

---

## Getting Started

### Prerequisites
- Python 3.8+
- A Telegram Bot Token
- Plume Cloud API Credentials (Authorization Header and Partner ID)

### Installation

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

### First-Time Use

1.  **Start a chat** with your bot in Telegram and send `/start`.
2.  The bot will prompt you to run `/setup`.
3.  Follow the on-screen instructions to provide your Plume API credentials (Authorization Header and Partner ID).
4.  Once setup is complete, the bot will suggest you run `/locations`.
5.  Use `/locations` to select the network you wish to monitor.
6.  Finally, run `/status` to see your first network health report. The bot will then guide you to other commands.
