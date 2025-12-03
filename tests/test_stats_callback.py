"""
Tests for the stats time range callback functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.handlers.location_stats import (
    stats_time_range_callback,
    create_time_range_keyboard,
    TIME_RANGES,
)


class TestStatsTimeRangeCallback:
    """Tests for the stats time range callback handler."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context with user data."""
        context = MagicMock()
        context.user_data = {
            "customer_id": "test_customer",
            "location_id": "test_location",
            "location_name": "Test Location",
        }
        return context

    @pytest.fixture
    def mock_update(self):
        """Create a mock update with callback query."""
        update = MagicMock()
        update.effective_user.id = 12345
        update.callback_query.data = "stats_7d"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message.text = "Current message"
        update.callback_query.message.reply_markup = create_time_range_keyboard()
        return update

    @pytest.mark.asyncio
    async def test_callback_skips_edit_when_content_unchanged(
        self, mock_update, mock_context
    ):
        """Test that edit_message_text is NOT called when message content is unchanged."""
        new_message = "Current message"
        new_keyboard = create_time_range_keyboard()

        # Set up mock to return identical content
        mock_update.callback_query.message.text = new_message
        mock_update.callback_query.message.reply_markup = new_keyboard

        with patch(
            "src.handlers.location_stats.fetch_and_format_stats",
            new=AsyncMock(return_value=new_message),
        ):
            await stats_time_range_callback(mock_update, mock_context)

        # answer() should be called, but edit_message_text should NOT be called
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_edits_when_message_content_changes(
        self, mock_update, mock_context
    ):
        """Test that edit_message_text IS called when message content changes."""
        old_message = "Old message"
        new_message = "New message"
        new_keyboard = create_time_range_keyboard()

        # Set up mock to have different content
        mock_update.callback_query.message.text = old_message
        mock_update.callback_query.message.reply_markup = new_keyboard

        with patch(
            "src.handlers.location_stats.fetch_and_format_stats",
            new=AsyncMock(return_value=new_message),
        ):
            await stats_time_range_callback(mock_update, mock_context)

        # Both answer() and edit_message_text should be called
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once_with(
            new_message, reply_markup=new_keyboard, parse_mode=None
        )

    @pytest.mark.asyncio
    async def test_callback_edits_when_keyboard_changes(
        self, mock_update, mock_context
    ):
        """Test that edit_message_text IS called when reply markup changes."""
        same_message = "Same message"
        old_keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Old", callback_data="old")]]
        )
        new_keyboard = create_time_range_keyboard()

        # Set up mock to have different keyboard
        mock_update.callback_query.message.text = same_message
        mock_update.callback_query.message.reply_markup = old_keyboard

        with patch(
            "src.handlers.location_stats.fetch_and_format_stats",
            new=AsyncMock(return_value=same_message),
        ):
            await stats_time_range_callback(mock_update, mock_context)

        # Both answer() and edit_message_text should be called
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once_with(
            same_message, reply_markup=new_keyboard, parse_mode=None
        )

    @pytest.mark.asyncio
    async def test_callback_handles_unknown_callback_data(self, mock_update, mock_context):
        """Test that unknown callback data is handled gracefully."""
        mock_update.callback_query.data = "stats_unknown"

        await stats_time_range_callback(mock_update, mock_context)

        # answer() should be called, edit_message_text should NOT be called
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_handles_missing_location(self, mock_update):
        """Test that missing location is handled with session expired message."""
        context = MagicMock()
        context.user_data = {}  # No location data

        await stats_time_range_callback(mock_update, context)

        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once_with(
            "Session expired. Please run /locations to select a location."
        )


class TestTimeRangeKeyboard:
    """Tests for the time range keyboard creation."""

    def test_create_time_range_keyboard_has_all_buttons(self):
        """Test that the time range keyboard has all expected buttons."""
        keyboard = create_time_range_keyboard()

        # Should have one row with 3 buttons
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 3

    def test_create_time_range_keyboard_callback_data(self):
        """Test that buttons have correct callback data."""
        keyboard = create_time_range_keyboard()

        callback_data_values = [
            button.callback_data for button in keyboard.inline_keyboard[0]
        ]

        assert "stats_3h" in callback_data_values
        assert "stats_24h" in callback_data_values
        assert "stats_7d" in callback_data_values

    def test_time_ranges_config_valid(self):
        """Test that TIME_RANGES configuration is valid."""
        expected_keys = {"stats_3h", "stats_24h", "stats_7d"}
        assert set(TIME_RANGES.keys()) == expected_keys

        for key, config in TIME_RANGES.items():
            assert "granularity" in config
            assert "limit" in config
            assert "label" in config
            assert config["granularity"] in ["hours", "days"]
            assert isinstance(config["limit"], int)
            assert config["limit"] > 0
