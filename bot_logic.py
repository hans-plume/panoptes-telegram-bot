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
Now I Have A Machine Gun. Ho Ho Ho - J. McClane
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

# Load Telegram bot token from environment
# IMPORTANT: This token authenticates the bot with Telegram servers
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

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
    ASK_AUTH_HEADER,       # State 1: Ask for Bearer token/authorization header
    ASK_PARTNER_ID,        # State 2: Ask for Plume Partner ID
    ASK_PLUME_API_BASE,    # State 3: Ask for Plume API base URL (optional)
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
    devices_count = location.get("connectedDeviceCount", 0)
    lines.append(f"Connected Devices: {devices_count}")
    
    return "\n".join(lines)


def format_wifi_networks(networks: list) -> str:
    """
    Format WiFi networks list for Telegram.
    
    Shows:
    - SSID (network name)
    - Enabled/disabled status
    - Security mode (WPA, WPA2, etc.)
    
    Args:
        networks: List of WiFi network dictionaries from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    if not networks:
        return "No WiFi networks configured."

    lines = ["📶 *WiFi Networks*:"]
    for net in networks:
        if not isinstance(net, dict):
            continue
        ssid = net.get("ssid", "Hidden SSID")
        enabled = net.get("enabled", True)
        mode = net.get("wpaMode", "Unknown")
        
        status = "✓ Enabled" if enabled else "✗ Disabled"
        lines.append(f"• {ssid}")
        lines.append(f"  {status} | Mode: {mode}")

    return "\n".join(lines)


def format_health_report(health: dict, location_name: str = "Location") -> str:
    """
    Format health analysis into human-friendly Telegram message.
    
    Converts health dictionary into readable report with:
    - Status emoji and summary
    - Online/offline status
    - Critical issues (if any)
    - Warnings (if any)
    - Disconnected devices list
    - Poor QoE traffic types
    
    Args:
        health: Health analysis dictionary from analyze_location_health()
        location_name: Name of location for display
        
    Returns:
        Formatted markdown string for Telegram
    """
    lines = [f"🏥 *Health Status for {location_name}*\n"]
    
    # Main status line with emoji indicator
    lines.append(health["summary"])
    lines.append("")

    # Connection status indicator
    status_icon = "✅" if health["online"] else "❌"
    lines.append(f"{status_icon} Connection: {'ONLINE' if health['online'] else 'OFFLINE'}")
    
    # Critical issues section (pods down, major service issues)
    if health["issues"]:
        lines.append("\n*Critical Issues:*")
        for issue in health["issues"]:
            lines.append(f"  {issue}")

    # Warnings section
    if health["warnings"]:
        lines.append("\n*Warnings:*")
        for warning in health["warnings"]:
            lines.append(f"  {warning}")

    # Disconnected devices count
    if health["disconnected_devices"]:
        lines.append(f"\n*Disconnected Devices ({len(health['disconnected_devices'])}):**")
        for device in health["disconnected_devices"][:5]:  # Show first 5
            lines.append(f"  • {device}")
        if len(health["disconnected_devices"]) > 5:
            lines.append(f"  ... and {len(health['disconnected_devices']) - 5} more")

    # Poor QoE traffic
    if health["poor_qoe_traffic"]:
        lines.append(f"\n*Traffic with Poor QoE:*")
        for traffic in health["poor_qoe_traffic"]:
            lines.append(f"  • {traffic}")

    # All clear message
    if not health["issues"] and not health["warnings"]:
        lines.append("\n✨ *Everything looks great!*")

    return "\n".join(lines)


# ============ DECORATORS FOR HANDLERS ============

def require_args(num_args: int, usage_text: str):
    """
    Decorator to validate that a command handler received enough arguments.
    If not, it replies with the usage text and stops execution.
    """
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if len(context.args) < num_args:
                await update.message.reply_markdown(usage_text)
                return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


# ============ TELEGRAM COMMAND HANDLERS ============
# These functions handle user commands. Each follows the same pattern:
# 1. Extract arguments (handled by decorator)
# 2. Validate arguments (handled by decorator)
# 3. Make API calls
# 4. Format responses
# 5. Send to user

@require_args(2, "Usage: `/nodes <customerId> <locationId>`")
async def handle_nodes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /nodes command - list all gateway nodes.
    Usage: /nodes <customerId> <locationId>
    """
    user_id = update.effective_user.id

    customer_id = context.args[0]
    location_id = context.args[1]

    try:
        nodes = await get_nodes_in_location(user_id, customer_id, location_id)
        reply = format_nodes_response(nodes)
        await update.message.reply_markdown(reply)
    except PlumeAPIError as e:
        await update.message.reply_text(f"⚠️ {e}")


@require_args(2, "Usage: `/devices <customerId> <locationId>`")
async def handle_devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /devices command - list connected devices.
    Usage: /devices <customerId> <locationId>
    """
    user_id = update.effective_user.id

    customer_id = context.args[0]
    location_id = context.args[1]

    try:
        devices = await get_connected_devices(user_id, customer_id, location_id)
        reply = format_devices_response(devices)
        await update.message.reply_markdown(reply)
    except PlumeAPIError as e:
        await update.message.reply_text(f"⚠️ {e}")


@require_args(2, "Usage: `/status <customerId> <locationId>`")
async def handle_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /status command - get comprehensive location health status.
    Usage: /status <customerId> <locationId>
    """
    user_id = update.effective_user.id

    customer_id = context.args[0]
    location_id = context.args[1]

    try:
        location = await get_location_status(user_id, customer_id, location_id)
        internet = await get_internet_health(user_id, customer_id, location_id)
        nodes = await get_nodes_in_location(user_id, customer_id, location_id)
        
        reply = format_location_health(location, internet)
        reply += f"\n\n{format_nodes_response(nodes)}"
        await update.message.reply_markdown(reply)
    except PlumeAPIError as e:
        await update.message.reply_text(f"⚠️ {e}")


@require_args(2, "Usage: `/wifi <customerId> <locationId>`")
async def handle_wifi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /wifi command - list WiFi networks.
    Usage: /wifi <customerId> <locationId>
    """
    user_id = update.effective_user.id

    customer_id = context.args[0]
    location_id = context.args[1]

    try:
        networks = await get_wifi_networks(user_id, customer_id, location_id)
        reply = format_wifi_networks(networks)
        await update.message.reply_markdown(reply)
    except PlumeAPIError as e:
        await update.message.reply_text(f"⚠️ {e}")


@require_args(2, "Usage: `/health <customerId> <locationId>`\n\n"
                 "Shows comprehensive service health including:\n"
                 "• Online status\n"
                 "• Connected pods/nodes\n"
                 "• Device connectivity\n"
                 "• Quality of Experience (QoE) indicators"
)
async def handle_health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /health command - comprehensive service health check.
    Shows:
    - If location is online
    - If any pods/nodes are disconnected
    - If any devices have poor QoE
    - Service disruption indicators
    Usage: /health <customerId> <locationId>
    """
    user_id = update.effective_user.id

    customer_id = context.args[0]
    location_id = context.args[1]

    try:
        # Fetch all health-related data in parallel
        location = await get_location_status(user_id, customer_id, location_id)
        service_level = await get_service_level(user_id, customer_id, location_id)
        nodes = await get_nodes_in_location(user_id, customer_id, location_id)
        devices = await get_connected_devices(user_id, customer_id, location_id)
        qoe = await get_qoe_stats(user_id, customer_id, location_id)

        # Analyze health
        health = analyze_location_health(location, service_level, nodes, devices, qoe)
        
        # Format and send
        location_name = location.get("name", "Your Location")
        reply = format_health_report(health, location_name)
        await update.message.reply_markdown(reply)

    except PlumeAPIError as e:
        await update.message.reply_text(f"⚠️ {e}")
    except Exception as e:
        logger.error("Error in health command: %s", e)
        await update.message.reply_text(
            "❌ An error occurred while checking health. Please try again later."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start command - Welcome message and command overview.
    
    Greets new users and explains how to:
    1. Set up authentication with /auth
    2. Use available commands
    """
    text = (
        "Hi! 👋 I'm your Plume Cloud bot.\n\n"
        "To get started, authenticate using:\n"
        "`/auth` – Set up OAuth credentials for Plume API access\n\n"
        "Once authenticated, you can use these commands:\n\n"
        "*Service Health & Status:*\n"
        "• `/health <customerId> <locationId>` – 🏥 Quick health check\n"
        "  Shows: online status, pod status, device connectivity, QoE\n\n"
        "*Detailed Status:*\n"
        "• `/status <customerId> <locationId>` – Overall location health\n"
        "• `/nodes <customerId> <locationId>` – Gateway/pod status\n"
        "• `/devices <customerId> <locationId>` – Connected devices\n"
        "• `/wifi <customerId> <locationId>` – WiFi networks\n\n"
        "*(Your credentials are never logged, only stored temporarily for API calls.)*"
    )
    await update.message.reply_markdown(text)


# ============ OAUTH AUTHENTICATION CONVERSATION HANDLER ============
# Multi-step authentication flow: SSO URL → Auth Header → Partner ID → API Base
# Uses ConversationHandler to maintain state across multiple messages

async def auth_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /auth command - Begin OAuth setup wizard.
    
    Initiates 4-step guided OAuth configuration process:
    Step 1: SSO URL endpoint
    Step 2: Authorization header (Bearer token)
    Step 3: Partner ID & API base URL (optional)
    """
    user_id = update.effective_user.id

    # Initialize auth config for this user with the static SSO URL
    if user_id not in user_auth:
        user_auth[user_id] = {}
    user_auth[user_id]["sso_url"] = PLUME_SSO_URL
    
    text = (
        "🔐 *OAuth Authentication Setup*\n\n"
        "I'll help you set up Plume API authentication. Please provide the following information:\n\n"
        "Step 1️⃣: What is your Authorization Header?\n"
        "(Example: Bearer abc123... or Basic base64...)\n\n"
        "_This is your client credentials in base64 format._"
    )
    await update.message.reply_markdown(text)
    return ASK_AUTH_HEADER


async def receive_auth_header(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation State 2: Receive and validate Authorization header.
    
    Stores the Bearer token or Basic auth header used for OAuth requests.
    This authenticates the bot with the SSO endpoint.
    """
    user_id = update.effective_user.id
    auth_header = update.message.text.strip()

    if not auth_header:
        await update.message.reply_text("❌ Authorization header cannot be empty.")
        return ASK_AUTH_HEADER

    user_auth[user_id]["auth_header"] = auth_header
    logger.info("Auth header stored for user %s (length: %d)", user_id, len(auth_header))

    text = (
        "✅ Authorization Header saved!\n\n"
        "Step 2️⃣: What is your Partner ID?\n"
        "(Example: eb0af9d0a7ab946dcb3b8ef5)\n\n"
        "_This identifies your Plume partner organization._"
    )
    await update.message.reply_markdown(text)
    return ASK_PARTNER_ID


async def receive_partner_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation State 3: Receive and validate Partner ID.
    
    Stores the Partner ID used in OAuth scope authorization.
    Validates minimum length (should be hex string ~24 chars).
    """
    user_id = update.effective_user.id
    partner_id = update.message.text.strip()

    if not partner_id or len(partner_id) < 20:
        await update.message.reply_text(
            "❌ Partner ID looks invalid. Please check and try again."
        )
        return ASK_PARTNER_ID

    user_auth[user_id]["partner_id"] = partner_id
    logger.info("Partner ID stored for user %s", user_id)

    text = (
        "✅ Partner ID saved!\n\n"
        "Step 3️⃣: What is your Plume API Base URL?\n"
        "(Example: https://api.plume.com or https://api.example.com)\n\n"
        "_If you're not sure, type /skip_"
    )
    await update.message.reply_markdown(text)
    return ASK_PLUME_API_BASE


async def receive_api_base(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation State 4: Receive and validate Plume API base URL.
    
    Optional: Custom API base URL for non-standard deployments.
    Can skip with /skip command to use default (PLUME_API_BASE constant).
    """
    user_id = update.effective_user.id
    api_base = update.message.text.strip()

    if api_base.startswith("/"):
        return await skip_api_base(update, context)

    if api_base and not api_base.startswith("http"):
        await update.message.reply_text(
            "❌ Invalid URL. Please provide a valid HTTPS URL or /skip."
        )
        return ASK_PLUME_API_BASE

    if api_base:
        user_auth[user_id]["plume_api_base"] = api_base
        logger.info("Plume API base URL stored for user %s", user_id)

    return await confirm_auth(update, context)


async def skip_api_base(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Skip custom API base URL - use default.
    
    Uses the default PLUME_API_BASE constant from configuration.
    User can still override later if needed.
    """
    """Skip setting custom API base URL."""
    user_id = update.effective_user.id
    # Use default
    user_auth[user_id]["plume_api_base"] = PLUME_API_BASE
    logger.info("Using default Plume API base URL for user %s", user_id)
    return await confirm_auth(update, context)


async def confirm_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation State 5 (final): Confirm OAuth configuration and exchange credentials for token.
    
    This final step:
    1. Displays the collected OAuth configuration
    2. Exchanges credentials for an OAuth access token via get_oauth_token()
    3. Stores the token and marks user as authenticated
    4. Presents available commands to the authenticated user
    
    If OAuth exchange fails, clears the partial configuration and prompts retry.
    """
    user_id = update.effective_user.id
    auth_config = user_auth.get(user_id)

    if not auth_config:
        await update.message.reply_text("❌ Authentication configuration incomplete.")
        return ConversationHandler.END

    # Display collected configuration before attempting OAuth
    text = (
        "📋 *Confirming Your Configuration*\n\n"
        f"SSO URL: `{auth_config.get('sso_url')[:50]}...`\n"
        f"Partner ID: `{auth_config.get('partner_id')}`\n"
        f"API Base: `{auth_config.get('plume_api_base', PLUME_API_BASE)}`\n\n"
        "🔄 Testing OAuth connection..."
    )
    await update.message.reply_markdown(text)

    try:
        # Exchange OAuth credentials for access token
        # This makes an OAuth 2.0 client credentials flow request to the SSO endpoint
        token_response = await get_oauth_token(auth_config)
        
        # Store the returned token(s) and mark as configured
        # token_response includes: access_token, expires_in, token_type, etc.
        user_auth[user_id].update(token_response)
        user_auth[user_id]["configured"] = True

        success_text = (
            "✅ *Authentication Successful!*\n\n"
            "🎉 You're all set! Your OAuth token has been obtained and will be "
            "automatically refreshed when needed.\n\n"
            "You can now use all bot commands:\n"
            "• `/health <customerId> <locationId>`\n"
            "• `/status <customerId> <locationId>`\n"
            "• `/nodes <customerId> <locationId>`\n"
            "• `/devices <customerId> <locationId>`\n"
            "• `/wifi <customerId> <locationId>`\n\n"
            "Type `/help` for more information."
        )
        await update.message.reply_markdown(success_text)
        logger.info("User %s authenticated successfully", user_id)

    except Exception as e:
        error_text = (
            f"❌ *Authentication Failed*\n\n"
            f"Error: {str(e)}\n\n"
            "Please verify your credentials and try again with `/auth`."
        )
        await update.message.reply_markdown(error_text)
        logger.error("Authentication failed for user %s: %s", user_id, e)
        # Clear failed auth attempt to allow retry
        if user_id in user_auth:
            del user_auth[user_id]

    return ConversationHandler.END


async def auth_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cancel OAuth authentication setup.
    
    Clears any partially collected OAuth configuration and ends the conversation.
    User can restart with /auth at any time.
    """
    user_id = update.effective_user.id
    # Only clear if not yet fully configured (to avoid losing working auth)
    if user_id in user_auth and not user_auth[user_id].get("configured"):
        del user_auth[user_id]
    
    await update.message.reply_text("❌ Authentication setup cancelled.")
    return ConversationHandler.END



# ============ TELEGRAM BOT SETUP & MAIN ============
# The main() function initializes the Telegram bot with all handlers:
# 1. ConversationHandler for multi-step OAuth authentication
# 2. CommandHandlers for single-step commands (health, status, nodes, etc.)
# All handlers use the ApplicationBuilder pattern from python-telegram-bot v20+

def main():
    """
    Initialize and run the Telegram bot.
    
    Sets up:
    1. ApplicationBuilder with bot token from TELEGRAM_BOT_TOKEN env var
    2. ConversationHandler for OAuth setup (entry point: /auth)
    3. Command handlers for all status/health queries
    4. Starts polling for incoming messages
    
    The bot maintains user authentication state in the global user_auth dict.
    Each authenticated user can query Plume Cloud API for their locations.
    """
    # Initialize bot application with token from environment
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # -------- OAUTH CONVERSATION HANDLER --------
    # Multi-step conversation for authenticating users with Plume API
    # Entry point: /auth command
    # States: ASK_SSO_URL → ASK_AUTH_HEADER → ASK_PARTNER_ID → ASK_PLUME_API_BASE
    # Fallback: /cancel command exits at any point
    auth_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("auth", auth_start)],  # /auth starts the flow
        states={
            # Step 2: Collect Authorization header (Bearer/Basic)
            ASK_AUTH_HEADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_auth_header)],
            
            # Step 3: Collect Partner ID
            ASK_PARTNER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_partner_id)],
            
            # Step 4: Collect API base URL (optional, can use /skip)
            ASK_PLUME_API_BASE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_base),
                CommandHandler("skip", skip_api_base),
            ],
        },
        # Allow /cancel to exit conversation at any point
        fallbacks=[CommandHandler("cancel", auth_cancel)],
    )

    # -------- REGISTER ALL HANDLERS --------
    app.add_handler(CommandHandler("start", start))  # /start - Welcome message
    app.add_handler(auth_conv_handler)               # /auth - OAuth setup
    app.add_handler(CommandHandler("health", handle_health_command))    # Health check
    app.add_handler(CommandHandler("nodes", handle_nodes_command))      # Node status
    app.add_handler(CommandHandler("devices", handle_devices_command))  # Device list
    app.add_handler(CommandHandler("status", handle_status_command))    # Location status
    app.add_handler(CommandHandler("wifi", handle_wifi_command))        # WiFi networks

    # Start polling for incoming updates
    app.run_polling()


if __name__ == "__main__":
    main()
