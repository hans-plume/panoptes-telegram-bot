"""
Location Stats Handlers Module

Telegram command and callback handlers for location online statistics.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from plume_api_client import PlumeAPIError, get_location_status
from src.api.online_stats import get_location_online_stats
from src.utils.stats_processor import process_online_stats
from src.utils.stats_formatter import format_online_stats_message

logger = logging.getLogger(__name__)

# Time range configuration
TIME_RANGES = {
    "stats_3h": {"granularity": "hours", "limit": 3, "label": "3h"},
    "stats_24h": {"granularity": "days", "limit": 1, "label": "24h"},
    "stats_7d": {"granularity": "days", "limit": 7, "label": "7d"},
}

DEFAULT_TIME_RANGE = "stats_7d"


def _get_stats_keyboard(selected: str = DEFAULT_TIME_RANGE) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for time range selection.

    Args:
        selected: Currently selected time range key.

    Returns:
        InlineKeyboardMarkup with time range buttons.
    """
    buttons = []
    for key, config in TIME_RANGES.items():
        label = config["label"]
        if key == "stats_3h":
            text = "3️⃣ Hrs"
        elif key == "stats_24h":
            text = "24️⃣ Hrs"
        else:
            text = "7️⃣ Days"

        if key == selected:
            text = f"✓ {text}"

        buttons.append(InlineKeyboardButton(text, callback_data=key))

    return InlineKeyboardMarkup([buttons])


async def _fetch_and_format_stats(
    user_id: int,
    customer_id: str,
    location_id: str,
    time_range_key: str,
) -> tuple[str, str]:
    """
    Fetch stats data and format the message.

    Args:
        user_id: Telegram user ID.
        customer_id: Plume customer ID.
        location_id: Plume location ID.
        time_range_key: Key from TIME_RANGES dict.

    Returns:
        Tuple of (formatted message, location name).

    Raises:
        PlumeAPIError: If API request fails.
    """
    config = TIME_RANGES.get(time_range_key, TIME_RANGES[DEFAULT_TIME_RANGE])
    granularity = config["granularity"]
    limit = config["limit"]

    # Fetch location info for name
    location_data = await get_location_status(user_id, customer_id, location_id)
    location_name = location_data.get("name", "Unknown Location")

    # Fetch online stats
    stats_data = await get_location_online_stats(
        user_id=user_id,
        customer_id=customer_id,
        location_id=location_id,
        granularity=granularity,
        limit=limit,
    )

    # Process and format
    metrics = process_online_stats(stats_data, granularity, limit)
    message = format_online_stats_message(location_name, metrics)

    return message, location_name


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /stats command to show location online statistics.

    Displays a graphical dashboard showing uptime percentage, status,
    incidents, and trend analysis with time range selection buttons.
    """
    reply_source = update.effective_message
    user_id = update.effective_user.id

    # Check if location is selected
    if "customer_id" not in context.user_data or "location_id" not in context.user_data:
        await reply_source.reply_text(
            "You haven't selected a location yet. Please run /locations first."
        )
        return

    await reply_source.reply_text("📊 Fetching connection status report...")

    try:
        customer_id = context.user_data["customer_id"]
        location_id = context.user_data["location_id"]

        message, _ = await _fetch_and_format_stats(
            user_id, customer_id, location_id, DEFAULT_TIME_RANGE
        )

        keyboard = _get_stats_keyboard(DEFAULT_TIME_RANGE)
        await reply_source.reply_text(
            message, reply_markup=keyboard, parse_mode=None
        )

    except PlumeAPIError as e:
        logger.error("API error in /stats: %s", e)
        await reply_source.reply_text(f"An API error occurred: {e}")
    except Exception as e:
        logger.error("Unexpected error in /stats: %s", e, exc_info=True)
        await reply_source.reply_text(
            "An unexpected error occurred while fetching stats."
        )


async def stats_time_range_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle callback queries for stats time range buttons.

    Updates the stats display when user clicks a different time range.
    """
    query = update.callback_query
    await query.answer()

    time_range_key = query.data
    if time_range_key not in TIME_RANGES:
        logger.warning("Invalid time range key: %s", time_range_key)
        return

    user_id = update.effective_user.id

    # Check if location is selected
    if "customer_id" not in context.user_data or "location_id" not in context.user_data:
        await query.edit_message_text(
            "Session expired. Please run /locations to select a location."
        )
        return

    try:
        customer_id = context.user_data["customer_id"]
        location_id = context.user_data["location_id"]

        message, _ = await _fetch_and_format_stats(
            user_id, customer_id, location_id, time_range_key
        )

        keyboard = _get_stats_keyboard(time_range_key)
        await query.edit_message_text(
            message, reply_markup=keyboard, parse_mode=None
        )

    except PlumeAPIError as e:
        logger.error("API error in stats callback: %s", e)
        await query.edit_message_text(f"An API error occurred: {e}")
    except Exception as e:
        logger.error("Unexpected error in stats callback: %s", e, exc_info=True)
        await query.edit_message_text(
            "An unexpected error occurred while fetching stats."
        )
