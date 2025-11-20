# Panoptes Telegram Bot

A production-ready Telegram bot for real-time monitoring of Plume Cloud networks. This bot uses the Plume API with OAuth 2.0 authentication to provide network health, status, and device information directly within Telegram.

## Features

- **Secure Authentication:** Guided, multi-step OAuth 2.0 setup to securely connect to the Plume API.
- **Real-time Monitoring:**
    - `/health`: Comprehensive health check (online status, pod connectivity, device QoE).
    - `/status`: Overall location health and speed test metrics.
    - `/nodes`: Detailed status of all gateways and pods.
    - `/devices`: List of all connected devices.
    - `/wifi`: Configured WiFi networks and their status.
- **Automatic Token Management:** Automatically refreshes expired OAuth tokens to ensure uninterrupted service.
- **Ready for Deployment:** Structured for easy deployment to cloud services like Google Cloud Platform.

## Project Structure

The project is structured for secure and maintainable deployment:

- `panoptes_bot.py`: The main entry point. Loads environment variables and starts the bot.
- `bot_logic.py`: Contains all the core business logic, command handlers, and Telegram-specific code.
- `plume_api_client.py`: A dedicated client for handling all communication with the Plume API, including OAuth and token refreshes.
- `requirements.txt`: A list of all Python dependencies.
- `.gitignore`: Ensures that secret files (like `.env`) are never committed to the repository.

## Local Setup and Running

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/hans-plume/panoptes-telegram-bot.git
    cd panoptes-telegram-bot
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create `.env` file for local secrets:** Create a file named `.env` in the project root and add your Telegram Bot Token. **This file is ignored by Git and should never be shared.**
    ```plaintext
    TELEGRAM_BOT_TOKEN="your_actual_bot_token_here"
    ```

5.  **Run the Bot:**
    ```bash
    python panoptes_bot.py
    ```

## Deployment

This bot is designed to be deployed on a cloud virtual machine, such as the **free `e2-micro` instance on Google Cloud Platform**. A `systemd` service can be used to ensure the bot runs persistently and restarts automatically.

For a detailed deployment guide, please refer to the documentation provided.

## Usage in Telegram

1.  **Start a chat** with your bot in Telegram.
2.  **Authenticate:** Use the `/auth` command to begin a guided setup to connect the bot to your Plume account. The bot will ask for your Authorization Header and Partner ID.
3.  **Monitor Your Network:** Once authenticated, you can use commands like `/health <customerId> <locationId>` to start monitoring your network.
