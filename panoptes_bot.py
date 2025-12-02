"""
Panoptes Telegram Bot - Plume Cloud Network Monitoring
========================================================

A production-ready Telegram bot for real-time monitoring of Plume Cloud networks.

Author: Hans V.
++ Nice Suit. John Philips, London. I Have Two Myself. -> H. Gruber ++
License: MIT
"""

import logging
import os
import traceback
import html
import json
from typing import Dict
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode

from plume_api_client import (
    set_user_auth,
    is_oauth_token_valid,
    get_oauth_token,
    get_locations_for_customer,
    get_nodes_in_location,
    get_location_status,
    get_wifi_networks,
    get_wan_stats,
    analyze_location_health,
    analyze_wan_stats,
    format_wan_analysis,
    PlumeAPIError,
    PLUME_SSO_URL,
    PLUME_API_BASE,
    PLUME_REPORTS_BASE,
)

from src.handlers.location_stats import stats_command, stats_time_range_callback

# ============ CONFIGURATION & LOGGING ============
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============ CONVERSATION STATES ============
(ASK_AUTH_HEADER, ASK_PARTNER_ID) = range(2)
(ASK_CUSTOMER_ID, SELECT_LOCATION) = range(2)

# ============ ERROR HANDLER ============

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a notification."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    tb_string = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
    logger.error(tb_string)

    # Try to notify the user
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "Sorry, a critical error occurred. The administrator has been notified."
            )
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")

# ============ HELPER FUNCTIONS ============

def get_reply_source(update: Update) -> Message:
    """Determine the correct message object to reply to."""
    return update.effective_message

def format_speed_test(speed_test_data: dict) -> str:
    if not speed_test_data or speed_test_data.get("status") != "succeeded":
        return "  - No recent speed test data available."
    download = speed_test_data.get('download', 0)
    upload = speed_test_data.get('upload', 0)
    latency = speed_test_data.get('rtt', 0)
    try:
        ended_at_str = speed_test_data.get('endedAt', '').split('.')[0]
        ended_at = datetime.fromisoformat(ended_at_str)
        ended_at_formatted = ended_at.strftime('%Y-%m-%d %H:%M:%S Z')
    except (ValueError, TypeError):
        ended_at_formatted = "N/A"
    return (
        f"  - *Download*: {download:.2f} Mbps\n"
        f"  - *Upload*: {upload:.2f} Mbps\n"
        f"  - *Latency*: {latency:.2f} ms\n"
        f"  - *Last Run*: {ended_at_formatted}"
    )

def format_pod_details(pod_list: list) -> str:
    if not pod_list:
        return "  - No pods found for this location."
    lines = []
    for pod in pod_list:
        name = pod.get('name', 'Unknown Pod')
        conn_state = pod.get('connection_state', 'unknown')
        health = pod.get('health_status', 'N/A')
        backhaul_raw = pod.get('backhaul_type', 'N/A')
        backhaul = "Mesh" if backhaul_raw.lower() == "wifi" else backhaul_raw.capitalize()
        if conn_state.lower() == "connected":
            status_icon = "✅" if health.lower() not in ["fair", "poor"] else "🟡"
            status_text = f"Online ({health} Health)" if health != "N/A" else "Online"
        else:
            status_icon = "🔴"
            status_text = "Disconnected"
        lines.append(f"  - `{name}`: {status_icon} {status_text} ({backhaul})")
        for alert in pod.get('alerts', []):
            lines.append(f"    - ⚠️ Alert: {alert}")
    return "\n".join(lines)

# ============ COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    reply_source = get_reply_source(update)
    if not is_oauth_token_valid(user.id):
        await reply_source.reply_text(f"Hi {user.first_name}! Welcome. Please run /setup to configure API access.")
    else:
        await reply_source.reply_text(f"Welcome back, {user.first_name}! Run /locations to select a network.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_source = get_reply_source(update)
    user_id = update.effective_user.id
    if 'customer_id' not in context.user_data or 'location_id' not in context.user_data:
        await reply_source.reply_text("You haven't selected a location yet. Please run /locations first.")
        return
    await reply_source.reply_text("Fetching enhanced network status... this may take a moment.")
    try:
        customer_id = context.user_data['customer_id']
        location_id = context.user_data['location_id']
        location_data = await get_location_status(user_id, customer_id, location_id)
        nodes_data = await get_nodes_in_location(user_id, customer_id, location_id)
        health_report = analyze_location_health(location_data, nodes_data)
        summary_parts = [
            f"📊 *Network Health Summary*: {health_report['summary']}\n",
            f"🏠 *Location*: {location_data.get('name', 'N/A')} (`{location_id}`)\n",
            "📡 *Pods Status*:",
            format_pod_details(health_report['pod_details']),
            "\n📶 *Last ISP Speed Test*:",
            format_speed_test(location_data.get("speedTest", {})),
            "\n" f"📱 *Total Devices Connected*: {health_report['total_connected_devices']}"
        ]
        summary = "\n".join(summary_parts)
        await reply_source.reply_markdown(summary)
        
        keyboard = [
            [InlineKeyboardButton("WAN Consumption Report", callback_data='nav_wan')],
            [InlineKeyboardButton("Online Stats Report", callback_data='nav_stats')],
            [InlineKeyboardButton("Get Node Details", callback_data='nav_nodes')],
            [InlineKeyboardButton("List WiFi Networks", callback_data='nav_wifi')],
            [InlineKeyboardButton("Change Location", callback_data='nav_locations')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await reply_source.reply_text('What would you like to do next?', reply_markup=reply_markup)

    except PlumeAPIError as e:
        await reply_source.reply_text(f"An API error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error in /status: {e}")
        await reply_source.reply_text("An unexpected error occurred.")

async def nodes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_source = get_reply_source(update)
    user_id = update.effective_user.id
    if 'customer_id' not in context.user_data or 'location_id' not in context.user_data:
        await reply_source.reply_text("Please select a location with /locations first.")
        return
    await reply_source.reply_text("Fetching node details...")
    try:
        nodes_data = await get_nodes_in_location(user_id, context.user_data['customer_id'], context.user_data['location_id'])
        if not nodes_data:
            await reply_source.reply_text("No nodes found for this location.")
            return

        report_parts = ["*Node Details*\n"]
        for node in nodes_data:
            name = node.get('defaultName', node.get('id'))
            report_parts.append(
                f"• *{name}*:\n"
                f"  - *State*: {node.get('connectionState', 'N/A')}\n"
                f"  - *Model*: {node.get('model', 'N/A')}\n"
                f"  - *Firmware*: {node.get('firmwareVersion', 'N/A')}\n"
                f"  - *MAC*: `{node.get('mac', 'N/A')}`\n"
                f"  - *IP*: `{node.get('ip', 'N/A')}`"
            )
        await reply_source.reply_markdown("\n".join(report_parts))
    except PlumeAPIError as e:
        await reply_source.reply_text(f"An API error occurred: {e}")

async def wifi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_source = get_reply_source(update)
    user_id = update.effective_user.id
    if 'customer_id' not in context.user_data or 'location_id' not in context.user_data:
        await reply_source.reply_text("Please select a location with /locations first.")
        return
    await reply_source.reply_text("Fetching WiFi networks...")
    try:
        wifi_data = await get_wifi_networks(user_id, context.user_data['customer_id'], context.user_data['location_id'])
        if not wifi_data:
            await reply_source.reply_text("No WiFi networks found.")
            return
        
        report_parts = ["*WiFi Network Configuration*\n"]
        for network in wifi_data:
            ssid = network.get("ssid", "N/A")
            enabled = "Enabled" if network.get("enable", False) else "Disabled"
            wpa_mode = network.get("wpaMode", "N/A")
            report_parts.append(
                f"• *{ssid}* ({enabled}):\n"
                f"  - *Security*: {wpa_mode}"
            )
        await reply_source.reply_markdown("\n".join(report_parts))
    except PlumeAPIError as e:
        await reply_source.reply_text(f"An API error occurred: {e}")

async def wan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_source = get_reply_source(update)
    user_id = update.effective_user.id
    if 'customer_id' not in context.user_data or 'location_id' not in context.user_data:
        await reply_source.reply_text("Please select a location with /locations first.")
        return
    
    await reply_source.reply_text("Fetching WAN consumption data for the last 24 hours...")
    
    try:
        customer_id = context.user_data['customer_id']
        location_id = context.user_data['location_id']
        
        wan_stats_data = await get_wan_stats(user_id, customer_id, location_id, period="daily")
        wan_analysis = analyze_wan_stats(wan_stats_data)
        
        report_str = format_wan_analysis(wan_analysis)
        await reply_source.reply_markdown(report_str)
        
    except PlumeAPIError as e:
        await reply_source.reply_text(f"An API error occurred while fetching WAN consumption data: {e}")
    except Exception as e:
        logger.error(f"An unexpected error in /wan: {e}")
        await reply_source.reply_text("An unexpected error occurred during WAN consumption analysis.")

# ============ NAVIGATION CALLBACK HANDLER ============

async def navigation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles callbacks from navigational keyboards."""
    query = update.callback_query
    await query.answer()
    
    await query.message.delete()
    
    command = query.data.split('_')[1]

    if command == 'nodes':
        await nodes(update, context)
    elif command == 'wifi':
        await wifi(update, context)
    elif command == 'locations':
        await locations_start(update, context)
    elif command == 'wan':
        await wan_command(update, context)
    elif command == 'stats':
        await stats_command(update, context)

# ============ LOCATION SELECTION CONVERSATION ============

async def locations_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_source = get_reply_source(update)
    user_id = update.effective_user.id
    if not is_oauth_token_valid(user_id):
        await reply_source.reply_text("API access is not configured. Please run /setup.")
        return ConversationHandler.END
    await reply_source.reply_text("Please provide the Customer ID to inspect.")
    return ASK_CUSTOMER_ID

async def customer_id_provided(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_source = get_reply_source(update)
    customer_id = reply_source.text.strip()
    context.user_data['customer_id'] = customer_id
    user_id = update.effective_user.id
    await reply_source.reply_text(f"Customer `{customer_id}` selected. Fetching locations...")
    try:
        locations = await get_locations_for_customer(user_id, customer_id)
        if not locations:
            await reply_source.reply_text("No locations found for this customer. Try /locations again.")
            return ConversationHandler.END
        keyboard = [[InlineKeyboardButton(loc.get('name', 'Unnamed'), callback_data=loc.get('id'))] for loc in locations]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await reply_source.reply_text('Please choose a location:', reply_markup=reply_markup)
        return SELECT_LOCATION
    except PlumeAPIError as e:
        await reply_source.reply_text(f"API Error: {e}\nPlease check the Customer ID and try again.")
        return ConversationHandler.END

async def location_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    location_id = query.data
    context.user_data['location_id'] = location_id
    await query.edit_message_text(text=f"Location selected: `{location_id}`\n\nNext, run /status to get a health report.")
    return ConversationHandler.END

async def locations_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_source = get_reply_source(update)
    await reply_source.reply_text("Location selection cancelled.")
    return ConversationHandler.END

# ============ AUTH SETUP CONVERSATION ============

async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_source = get_reply_source(update)
    await reply_source.reply_text(
        "Starting OAuth setup...\n\n"
        "**Step 1 of 2:** Please provide your Plume authorization header.\n"
        "Send /cancel at any time to abort."
    )
    return ASK_AUTH_HEADER

async def ask_partner_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['auth_header'] = update.message.text
    await update.message.reply_text("**Step 2 of 2:** Great. Now, please provide your Plume Partner ID.")
    return ASK_PARTNER_ID

async def confirm_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_source = get_reply_source(update)
    partner_id = reply_source.text
    auth_header = context.user_data.get('auth_header')
    user_id = update.effective_user.id
    auth_config = {"sso_url": PLUME_SSO_URL, "auth_header": auth_header, "partner_id": partner_id, "plume_api_base": PLUME_API_BASE, "plume_reports_base": PLUME_REPORTS_BASE}
    set_user_auth(user_id, auth_config)
    await reply_source.reply_text("Testing API connection...")
    try:
        new_token_data = await get_oauth_token(auth_config)
        auth_config.update(new_token_data)
        await reply_source.reply_text("✅ **Success!** API connection is working.\n\nNext, run /locations to begin.")
        return ConversationHandler.END
    except (PlumeAPIError, ValueError) as e:
        await reply_source.reply_text(f"❌ **Failed!** {e}\nPlease run /setup again.")
        return ConversationHandler.END

async def cancel_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_source = get_reply_source(update)
    await reply_source.reply_text("OAuth setup cancelled.")
    return ConversationHandler.END

# ============ BOT MAIN ENTRY POINT ============

def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

    application = ApplicationBuilder().token(token).build()

    application.add_error_handler(error_handler)

    setup_handler = ConversationHandler(
        entry_points=[CommandHandler("setup", setup_start)],
        states={
            ASK_AUTH_HEADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_partner_id)],
            ASK_PARTNER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_auth)],
        },
        fallbacks=[CommandHandler("cancel", cancel_setup)],
    )

    locations_handler = ConversationHandler(
        entry_points=[CommandHandler("locations", locations_start)],
        states={
            ASK_CUSTOMER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, customer_id_provided)],
            SELECT_LOCATION: [CallbackQueryHandler(location_selected, pattern='^((?!nav_).)*$')],
        },
        fallbacks=[CommandHandler("cancel", locations_cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("nodes", nodes))
    application.add_handler(CommandHandler("wifi", wifi))
    application.add_handler(CommandHandler("wan", wan_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(setup_handler)
    application.add_handler(locations_handler)
    application.add_handler(CallbackQueryHandler(navigation_handler, pattern='^nav_'))
    application.add_handler(CallbackQueryHandler(stats_time_range_callback, pattern='^stats_'))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
