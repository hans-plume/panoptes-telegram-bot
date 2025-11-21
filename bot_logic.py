"""
Panoptes Telegram Bot - Plume Cloud Network Monitoring
========================================================

A production-ready Telegram bot for real-time monitoring of Plume Cloud networks.

Features:
- OAuth 2.0 authentication for secure API access
- Real-time health monitoring (nodes, devices, QoE)
- Multi-step guided OAuth setup
- Comprehensive service status reporting
- Automatic token refresh

Author: Hans V.
+ Nice Suit. John Philips, London. I Have Two Myself + H. Gruber +
License: MIT
"""

import logging
import os
from typing import Optional

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from plume_api_client import (
    set_user_auth,
    get_user_auth,
    is_oauth_token_valid,
    get_oauth_token,
    get_nodes_in_location,
    get_connected_devices,
    get_location_status,
    get_wifi_networks,
    get_service_level,
    get_qoe_stats,
    get_internet_health,
    analyze_location_health,
    PlumeAPIError,
    PLUME_SSO_URL,
    PLUME_API_BASE,
    user_auth,
)

# ============ CONFIGURATION & INITIALIZATION ============

# Configure logging for debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ CONVERSATION STATE MACHINE ============
# These constants define the OAuth authentication flow states
# Each state represents a step in the 4-step OAuth setup process
(
    ASK_AUTH_HEADER,       # State 1: Ask for authorization header
    ASK_PARTNER_ID,        # State 2: Ask for Plume Partner ID
    CONFIRM_AUTH,          # State 4: Confirm and test OAuth connection
) = range(4)


# ============ RESPONSE FORMATTERS ============
# These functions format raw API data into Telegram-friendly markdown messages
# Each formatter takes API response data and returns a formatted string

def format_nodes_response(nodes: list) -> str:
    """
    Format nodes/gateways list for Telegram display.
    
    Transforms API node data into a readable list with:
    - Node nickname/ID
    - Connection status
    - Model information
    - Firmware version
    
    Args:
        nodes: List of node dictionaries from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    if not nodes:
        return "No nodes found for this location."

    lines = ["📡 *Nodes/Gateways*:"]
    for node in nodes:
        if not isinstance(node, dict):
            continue
        nickname = node.get("nickname", node.get("id", "Unknown"))
        status = node.get("connectionState", node.get("status", "unknown"))
        firmware = node.get("firmwareVersion", "N/A")
        model = node.get("model", "N/A")
        
        lines.append(f"• {nickname}")
        lines.append(f"  Status: *{status}*")
        lines.append(f"  Model: {model}")
        lines.append(f"  Firmware: {firmware}")

    return "\n".join(lines)


def format_devices_response(devices: list) -> str:
    """
    Format connected devices list for Telegram display.
    
    Shows:
    - Device name
    - Device type (phone, laptop, etc.)
    - MAC address
    - Connection status
    - Limits to 10 devices for readability
    
    Args:
        devices: List of device dictionaries from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    if not devices:
        return "No devices connected to this location."

    lines = ["📱 *Connected Devices*:"]
    count = 0
    for device in devices[:10]:  # Limit to 10 for readability
        if not isinstance(device, dict):
            continue
        mac = device.get("mac", "N/A")
        device_type = device.get("type", "Unknown")
        nickname = device.get("nickname", "Unnamed")
        status = device.get("connected", device.get("status", "unknown"))
        
        lines.append(f"• {nickname} ({device_type})")
        lines.append(f"  MAC: `{mac}`")
        lines.append(f"  Status: {status}")
        count += 1

    if len(devices) > 10:
        lines.append(f"\n... and {len(devices) - 10} more devices")

    return "\n".join(lines)


def format_location_health(location: dict, internet: dict) -> str:
    """
    Format location health and internet status for Telegram.
    
    Displays:
    - Location name
    - Internet/backhaul connection status
    - Speed test metrics (if available)
    - Connected device count
    
    Args:
        location: Location data dictionary from API
        internet: Internet health data from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    lines = ["🏠 *Location Health*:"]
    
    location_name = location.get("name", "Unknown Location")
    lines.append(f"*{location_name}*")
    
    # Internet health/backhaul status
    backhaul_status = internet.get("status", "unknown")
    lines.append(f"\nInternet: *{backhaul_status}*")
    
    # Speed test data if available - shows average speeds
    speed_tests = location.get("lastThirtyDaysSpeedTestAverages", {})
    if speed_tests:
        down = speed_tests.get("downloadMbps", "N/A")
        up = speed_tests.get("uploadMbps", "N/A")
        lines.append(f"Download: {down} Mbps | Upload: {up} Mbps")
    
    # Connected devices count for at-a-glance view
    devices_count = location.get("connectedDevicesCount", 0)
    lines.append(f"Connected Devices: {devices_count}")
    
    return "\n".join(lines)


def format_wifi_networks(networks: list) -> str:
    """
    Format WiFi networks (SSIDs) for Telegram display.
    
    Shows:
    - SSID name
    - Security type (WPA2, etc.)
    - Password (if available)
    
    Args:
        networks: List of network dictionaries from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    if not networks:
        return "No WiFi networks found."

    lines = ["📶 *WiFi Networks*:"]
    for network in networks:
        ssid = network.get("ssid", "Unknown SSID")
        security = network.get("security", "N/A")
        password = network.get("key", "Not available")
        
        lines.append(f"• SSID: *{ssid}*")
        lines.append(f"  Security: {security}")
        lines.append(f"  Password: `{password}`")

    return "\n".join(lines)


def format_service_level(service_level: dict) -> str:
    """
    Format service level/QoE stats for Telegram display.
    
    Shows:
    - Overall QoE score
    - Individual scores for streaming, gaming, etc.
    
    Args:
        service_level: Service level dictionary from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    lines = ["⭐ *Service Level (QoE)*:"]
    
    overall_score = service_level.get("overall", {}).get("score", "N/A")
    lines.append(f"Overall Score: *{overall_score}*")
    
    for category, data in service_level.items():
        if category != "overall" and isinstance(data, dict):
            score = data.get("score", "N/A")
            lines.append(f"• {category.title()}: {score}")
            
    return "\n".join(lines)


# ============ TELEGRAM COMMAND HANDLERS ============
# These functions are called when a user sends a specific command

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    
    Greets the user and checks if OAuth is configured.
    If not configured, prompts the user to start the setup.
    """
    user = update.effective_user
    if not is_oauth_token_valid(user.id):
        await update.message.reply_text(
            f"Hi {user.first_name}! Welcome to Panoptes Bot.\n"
            "Your Plume API access is not configured. "
            "Please run /setup to begin."
        )
    else:
        await update.message.reply_text(
            f"Hi {user.first_name}! Welcome back.\n"
            "Your API access is configured. Run /status to get a network report."
        )


async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start the multi-step OAuth setup process.
    
    Asks for the first piece of information: the authorization header.
    """
    await update.message.reply_text(
        "Starting OAuth setup...\n\n"
        "**Step 1 of 3:** Please provide your Plume authorization header.\n"
        "This should look like `Basic <your_long_token>`.\n\n"
        "Send /cancel at any time to abort."
    )
    return ASK_AUTH_HEADER


async def ask_partner_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle the authorization header and ask for the Partner ID.
    
    Stores the auth header in context and proceeds to the next step.
    """
    context.user_data['auth_header'] = update.message.text
    await update.message.reply_text(
        "**Step 2 of 3:** Great. Now, please provide your Plume Partner ID."
    )
    return ASK_PARTNER_ID


async def ask_plume_api_base(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle the Partner ID and ask for the API base URL.
    
    Stores the Partner ID and gives the option to provide a custom API URL.
    """
    context.user_data['partner_id'] = update.message.text
    await update.message.reply_text(
        "**Step 3 of 3:** Almost done. What is your Plume API base URL?\n"
        f"If you don't know, just send `default` to use `{PLUME_API_BASE}`."
    )
    return ASK_PLUME_API_BASE


async def confirm_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle the API base URL and finalize the OAuth setup.
    
    Sets all user-provided auth details, tests the connection,
    and reports success or failure to the user.
    """
    api_base = update.message.text
    if api_base.lower() == 'default':
        api_base = PLUME_API_BASE

    auth_header = context.user_data.get('auth_header')
    partner_id = context.user_data.get('partner_id')
    user_id = update.effective_user.id

    set_user_auth(user_id, auth_header, partner_id, api_base)

    await update.message.reply_text("Testing API connection...")
    
    try:
        if is_oauth_token_valid(user_id):
            await update.message.reply_text(
                "✅ **Success!** API connection is working.\n"
                "You can now use commands like /status."
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ **Failed!** Could not validate the token. "
                "Please check your details and run /setup again."
            )
            return ConversationHandler.END
    except PlumeAPIError as e:
        await update.message.reply_text(f"API Error: {e}")
        return ConversationHandler.END


async def cancel_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel the multi-step OAuth setup conversation.
    """
    await update.message.reply_text("OAuth setup cancelled.")
    return ConversationHandler.END


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /status command.
    
    Fetches and displays a comprehensive network status report, including:
    - Location health
    - Nodes/gateways
    - Connected devices
    - WiFi networks
    - Service level (QoE)
    """
    user = update.effective_user
    if not is_oauth_token_valid(user.id):
        await update.message.reply_text("API access is not configured. Please run /setup.")
        return

    await update.message.reply_text("Fetching network status... this may take a moment.")
    
    try:
        # Fetch all data points in parallel
        location_data = get_location_status(user.id)
        internet_data = get_internet_health(user.id)
        nodes_data = get_nodes_in_location(user.id)
        devices_data = get_connected_devices(user.id)
        wifi_data = get_wifi_networks(user.id)
        service_level_data = get_service_level(user.id)

        # Format and send each piece of information as a separate message
        await update.message.reply_markdown(format_location_health(location_data, internet_data))
        await update.message.reply_markdown(format_nodes_response(nodes_data))
        await update.message.reply_markdown(format_devices_response(devices_data))
        await update.message.reply_markdown(format_wifi_networks(wifi_data))
        await update.message.reply_markdown(format_service_level(service_level_data))

    except PlumeAPIError as e:
        await update.message.reply_text(f"An API error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in /status: {e}")
        await update.message.reply_text("An unexpected error occurred.")


# ============ BOT MAIN ENTRY POINT ============

def main(token: str) -> None:
    """
    The main function to run the bot.
    
    Initializes the Telegram application, sets up all command handlers,
    and starts the bot's polling loop.
    
    Args:
        token: The Telegram Bot API token.
    """
    application = ApplicationBuilder().token(token).build()

    # Setup conversation handler for multi-step /setup command
    setup_handler = ConversationHandler(
        entry_points=[CommandHandler("setup", setup_start)],
        states={
            ASK_AUTH_HEADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_partner_id)],
            ASK_PARTNER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_plume_api_base)],
            ASK_PLUME_API_BASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_auth)],
        },
        fallbacks=[CommandHandler("cancel", cancel_setup)],
    )

    # Add all handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(setup_handler)
    application.add_handler(CommandHandler("status", status))

    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling()
