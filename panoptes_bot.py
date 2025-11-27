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
from typing import Dict

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# This will fail if plume_api_client.py is not in the same directory
from plume_api_client import (
    set_user_auth,
    is_oauth_token_valid,
    get_oauth_token,
    get_nodes_in_location,
    get_connected_devices,
    get_location_status,
    get_wifi_networks,
    get_service_level,
    get_internet_health,
    analyze_location_health,
    PlumeAPIError,
    PLUME_SSO_URL,
    PLUME_API_BASE,
)

# ============ CONFIGURATION & INITIALIZATION ============

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ CONVERSATION STATE MACHINE (2-STEP SETUP) ============
(
    ASK_AUTH_HEADER,
    ASK_PARTNER_ID,
) = range(2)


# ============ TELEGRAM COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_oauth_token_valid(user.id):
        await update.message.reply_text(
            f"Hi {user.first_name}! Welcome to Panoptes Bot.\n"
            "Your Plume API access is not configured. Please run /setup to begin."
        )
    else:
        await update.message.reply_text(
            f"Hi {user.first_name}! Welcome back.\n"
            "Your API access is configured. Run /status to get a network report."
        )

async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Starting OAuth setup...\n\n"
        "**Step 1 of 2:** Please provide your Plume authorization header.\n"
        "This should look like `Basic <your_long_token>`.\n\n"
        "Send /cancel at any time to abort."
    )
    return ASK_AUTH_HEADER

async def ask_partner_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['auth_header'] = update.message.text
    await update.message.reply_text(
        "**Step 2 of 2:** Great. Now, please provide your Plume Partner ID."
    )
    return ASK_PARTNER_ID

async def confirm_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    partner_id = update.message.text
    auth_header = context.user_data.get('auth_header')
    user_id = update.effective_user.id

    auth_config = {
        "sso_url": PLUME_SSO_URL,
        "auth_header": auth_header,
        "partner_id": partner_id,
        "plume_api_base": PLUME_API_BASE,
    }
    set_user_auth(user_id, auth_config)

    await update.message.reply_text("Testing API connection...")
    
    try:
        new_token_data = await get_oauth_token(auth_config)
        auth_config.update(new_token_data)
        
        await update.message.reply_text(
            "✅ **Success!** API connection is working.\n"
            "You can now use commands like /status."
        )
        return ConversationHandler.END
    except (PlumeAPIError, ValueError) as e:
        await update.message.reply_text(f"❌ **Failed!** {e}\nPlease check your details and run /setup again.")
        return ConversationHandler.END

async def cancel_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("OAuth setup cancelled.")
    return ConversationHandler.END

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_oauth_token_valid(user.id):
        await update.message.reply_text("API access is not configured. Please run /setup.")
        return

    await update.message.reply_text("Fetching network status... this may take a moment.")
    
    try:
        # NOTE: In a real application, you need a way to get the customer and location IDs.
        # This is a placeholder and will fail if not replaced.
        customer_id = "YOUR_CUSTOMER_ID"  # <-- REPLACE
        location_id = "YOUR_LOCATION_ID"  # <-- REPLACE

        location_data = await get_location_status(user.id, customer_id, location_id)
        service_level_data = await get_service_level(user.id, customer_id, location_id)
        nodes_data = await get_nodes_in_location(user.id, customer_id, location_id)
        devices_data = await get_connected_devices(user.id, customer_id, location_id)
        qoe_data = {}
        try:
            qoe_data = await get_qoe_stats(user.id, customer_id, location_id)
        except PlumeAPIError:
            logger.warning("Could not fetch QoE stats for location %s.", location_id)

        health_report = analyze_location_health(location_data, service_level_data, nodes_data, devices_data, qoe_data)
        
        # Create a summary message
        summary = (
            f"📊 *Network Health Summary*: {health_report['summary']}\n\n"
            f"🏠 *Location*: {location_data.get('name', 'N/A')}\n"
            f"📡 *Pods Online*: {len(nodes_data) - len(health_report['disconnected_nodes'])}/{len(nodes_data)}\n"
            f"📱 *Devices Connected*: {location_data.get('connectedDevicesCount', 'N/A')}"
        )
        await update.message.reply_markdown(summary)

    except PlumeAPIError as e:
        await update.message.reply_text(f"An API error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in /status: {e}")
        await update.message.reply_text("An unexpected error occurred. Check logs for details.")


# ============ BOT MAIN ENTRY POINT ============

def main() -> None:
    """Sets up and runs the Telegram bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

    application = ApplicationBuilder().token(token).build()

    # A 2-step conversation for /setup
    setup_handler = ConversationHandler(
        entry_points=[CommandHandler("setup", setup_start)],
        states={
            ASK_AUTH_HEADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_partner_id)],
            ASK_PARTNER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_auth)],
        },
        fallbacks=[CommandHandler("cancel", cancel_setup)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(setup_handler)
    application.add_handler(CommandHandler("status", status))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
