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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from plume_api_client import (
    set_user_auth,
    is_oauth_token_valid,
    get_oauth_token,
    get_locations_for_customer,
    get_nodes_in_location,
    get_location_status,
    get_connected_devices,
    get_service_level,
    analyze_location_health,
    PlumeAPIError,
    PLUME_SSO_URL,
    PLUME_API_BASE,
)

# ============ CONFIGURATION & LOGGING ============
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============ CONVERSATION STATES ============
(ASK_AUTH_HEADER, ASK_PARTNER_ID) = range(2)
(ASK_CUSTOMER_ID, SELECT_LOCATION) = range(2) # For new /locations conversation

# ============ COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_oauth_token_valid(user.id):
        await update.message.reply_text(f"Hi {user.first_name}! Welcome. Please run /setup to configure API access.")
    else:
        await update.message.reply_text(f"Welcome back, {user.first_name}! Run /locations to select a network or /status to get a report.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_oauth_token_valid(user_id):
        await update.message.reply_text("API access is not configured. Please run /setup.")
        return

    if 'customer_id' not in context.user_data or 'location_id' not in context.user_data:
        await update.message.reply_text("You haven't selected a location yet. Please run /locations first.")
        return

    await update.message.reply_text("Fetching network status... this may take a moment.")
    
    try:
        customer_id = context.user_data['customer_id']
        location_id = context.user_data['location_id']

        location_data = await get_location_status(user_id, customer_id, location_id)
        service_level_data = await get_service_level(user_id, customer_id, location_id)
        nodes_data = await get_nodes_in_location(user_id, customer_id, location_id)
        devices_data = await get_connected_devices(user_id, customer_id, location_id)
        
        health_report = analyze_location_health(location_data, service_level_data, nodes_data, devices_data, {})
        
        summary = (
            f"📊 *Network Health Summary*: {health_report['summary']}\n\n"
            f"🏠 *Location*: {location_data.get('name', 'N/A')} (`{location_id}`)\n"
            f"📡 *Pods Online*: {len(nodes_data) - len(health_report['disconnected_nodes'])}/{len(nodes_data)}\n"
            f"📱 *Devices Connected*: {location_data.get('connectedDevicesCount', 'N/A')}"
        )
        await update.message.reply_markdown(summary)

    except PlumeAPIError as e:
        await update.message.reply_text(f"An API error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error in /status: {e}")
        await update.message.reply_text("An unexpected error occurred.")

# ============ LOCATION SELECTION CONVERSATION ============

async def locations_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the location selection process by asking for a Customer ID."""
    user_id = update.effective_user.id
    if not is_oauth_token_valid(user_id):
        await update.message.reply_text("API access is not configured. Please run /setup.")
        return ConversationHandler.END

    await update.message.reply_text("Please provide the Customer ID you want to inspect.")
    return ASK_CUSTOMER_ID

async def customer_id_provided(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the provided Customer ID and fetches its locations."""
    customer_id = update.message.text.strip()
    context.user_data['customer_id'] = customer_id
    user_id = update.effective_user.id

    await update.message.reply_text(f"Customer `{customer_id}` selected. Fetching locations...")

    try:
        locations = await get_locations_for_customer(user_id, customer_id)
        if not locations:
            await update.message.reply_text("Could not find any locations for this customer. Please try /locations again with a different ID.")
            return ConversationHandler.END

        keyboard = []
        for loc in locations:
            callback_data = loc.get('id')
            button = InlineKeyboardButton(loc.get('name', 'Unnamed Location'), callback_data=callback_data)
            keyboard.append([button])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Please choose a location:', reply_markup=reply_markup)
        return SELECT_LOCATION

    except PlumeAPIError as e:
        await update.message.reply_text(f"API Error: {e}\n\nPlease check the Customer ID and try again.")
        return ConversationHandler.END

async def location_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's location choice."""
    query = update.callback_query
    await query.answer()

    location_id = query.data
    context.user_data['location_id'] = location_id

    await query.edit_message_text(text=f"Location selected: `{location_id}`\nRun /status to get a report.")
    return ConversationHandler.END

async def locations_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the location selection."""
    await update.message.reply_text("Location selection cancelled.")
    return ConversationHandler.END

# ============ AUTH SETUP CONVERSATION ============

async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
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
    partner_id = update.message.text
    auth_header = context.user_data.get('auth_header')
    user_id = update.effective_user.id

    auth_config = {
        "sso_url": PLUME_SSO_URL, "auth_header": auth_header,
        "partner_id": partner_id, "plume_api_base": PLUME_API_BASE,
    }
    set_user_auth(user_id, auth_config)

    await update.message.reply_text("Testing API connection...")
    try:
        new_token_data = await get_oauth_token(auth_config)
        auth_config.update(new_token_data)
        await update.message.reply_text("✅ **Success!** API connection is working.\nRun /locations to begin.")
        return ConversationHandler.END
    except (PlumeAPIError, ValueError) as e:
        await update.message.reply_text(f"❌ **Failed!** {e}\nPlease check your details and run /setup again.")
        return ConversationHandler.END

async def cancel_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("OAuth setup cancelled.")
    return ConversationHandler.END

# ============ BOT MAIN ENTRY POINT ============

def main() -> None:
    """Sets up and runs the Telegram bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

    application = ApplicationBuilder().token(token).build()

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
            SELECT_LOCATION: [CallbackQueryHandler(location_selected)],
        },
        fallbacks=[CommandHandler("cancel", locations_cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(setup_handler)
    application.add_handler(locations_handler)

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
