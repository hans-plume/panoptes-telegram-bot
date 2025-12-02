"""
Location Stats Handlers

Telegram command and callback handlers for the /stats command.
"""

import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from plume_api_client import PlumeAPIError, get_location_status
from src.api.online_stats import get_location_online_stats
from src.utils.stats_processor import process_online_stats
from src.utils.stats_formatter import format_online_stats_message

logger = logging.getLogger(__name__)

# Time range configurations
TIME_RANGES = {
    "stats_3h": {"granularity": "hours", "limit": 3, "label": "3 Hrs"},
    "stats_24h": {"granularity": "days", "limit": 1, "label": "24 Hrs"},
    "stats_7d": {"granularity": "days", "limit": 7, "label": "7 Days"},
}


def create_time_range_keyboard() -> InlineKeyboardMarkup:
    """
    Create the inline keyboard for time range selection.

    Returns:
        InlineKeyboardMarkup with time range buttons.
    """
    keyboard = [
        [
            InlineKeyboardButton("3️⃣ Hrs", callback_data="stats_3h"),
            InlineKeyboardButton("2️⃣4️⃣ Hrs", callback_data="stats_24h"),
            InlineKeyboardButton("7️⃣ Days", callback_data="stats_7d"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def fetch_and_format_stats(
    user_id: int,
    customer_id: str,
    location_id: str,
    granularity: str,
    limit: int,
    location_name: Optional[str] = None,
) -> str:
    """
    Fetch online stats and format them into a message.

    Args:
        user_id: Telegram user ID.
        customer_id: Plume customer ID.
        location_id: Location ID.
        granularity: Time granularity ('hours' or 'days').
        limit: Number of periods.
        location_name: Optional location name for display.

    Returns:
        Formatted stats message.

    Raises:
        PlumeAPIError: If API request fails.
    """
    # Fetch the stats
    stats_response = await get_location_online_stats(
        user_id=user_id,
        customer_id=customer_id,
        location_id=location_id,
        granularity=granularity,
        limit=limit,
    )

    # Process the response
    processed_stats = process_online_stats(stats_response, granularity, limit)

    # Use location_id as fallback if no name provided
    display_name = location_name or location_id

    # Format the message
    return format_online_stats_message(display_name, processed_stats)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /stats command.

    Shows the connection status report with time range selection buttons.
    """
    reply_source = update.effective_message
    user_id = update.effective_user.id

    # Check if location is selected
    if "customer_id" not in context.user_data or "location_id" not in context.user_data:
        await reply_source.reply_text(
            "You haven't selected a location yet. Please run /locations first."
        )
        return

    await reply_source.reply_text("Fetching connection status data...")

    try:
        customer_id = context.user_data["customer_id"]
        location_id = context.user_data["location_id"]

        # Try to get location name
        location_name = location_id
        try:
            location_data = await get_location_status(user_id, customer_id, location_id)
            location_name = location_data.get("name", location_id)
        except PlumeAPIError as e:
            logger.debug("Could not fetch location name, using ID as fallback: %s", e)

        # Default to 7 days view
        message = await fetch_and_format_stats(
            user_id=user_id,
            customer_id=customer_id,
            location_id=location_id,
            granularity="days",
            limit=7,
            location_name=location_name,
        )

        # Store location name for callback use
        context.user_data["location_name"] = location_name

        # Send message with time range keyboard
        keyboard = create_time_range_keyboard()
        await reply_source.reply_text(
            message, reply_markup=keyboard, parse_mode=None
        )

    except PlumeAPIError as e:
        logger.error("API error in /stats: %s", e)
        await reply_source.reply_text(f"An API error occurred: {e}")
    except Exception as e:
        logger.error("Unexpected error in /stats: %s", e)
        await reply_source.reply_text("An unexpected error occurred.")


async def stats_time_range_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle callback queries for time range selection.

    Updates the stats display based on the selected time range.
    """
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    user_id = update.effective_user.id

    if callback_data not in TIME_RANGES:
        logger.warning("Unknown stats callback data: %s", callback_data)
        return

    # Check if location is selected
    if "customer_id" not in context.user_data or "location_id" not in context.user_data:
        await query.edit_message_text(
            "Session expired. Please run /locations to select a location."
        )
        return

    try:
        customer_id = context.user_data["customer_id"]
        location_id = context.user_data["location_id"]
        location_name = context.user_data.get("location_name", location_id)

        time_range = TIME_RANGES[callback_data]

        # Fetch and format stats
        message = await fetch_and_format_stats(
            user_id=user_id,
            customer_id=customer_id,
            location_id=location_id,
            granularity=time_range["granularity"],
            limit=time_range["limit"],
            location_name=location_name,
        )

        # Update message with new stats
        keyboard = create_time_range_keyboard()
        await query.edit_message_text(
            message, reply_markup=keyboard, parse_mode=None
        )

    except PlumeAPIError as e:
        logger.error("API error in stats callback: %s", e)
        await query.edit_message_text(f"An API error occurred: {e}")
    except Exception as e:
        logger.error("Unexpected error in stats callback: %s", e)
        await query.edit_message_text("An unexpected error occurred.")
