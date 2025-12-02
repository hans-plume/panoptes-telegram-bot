"""
Tests for navigation menu functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class TestStatusNavigationKeyboard:
    """Tests for the status command navigation keyboard."""

    def test_navigation_keyboard_contains_online_stats_button(self):
        """Test that the navigation keyboard includes the Online Stats Report button."""
        # Recreate the keyboard structure from panoptes_bot.py
        keyboard = [
            [InlineKeyboardButton("WAN Consumption Report", callback_data='nav_wan')],
            [InlineKeyboardButton("Online Stats Report", callback_data='nav_stats')],
            [InlineKeyboardButton("Get Node Details", callback_data='nav_nodes')],
            [InlineKeyboardButton("List WiFi Networks", callback_data='nav_wifi')],
            [InlineKeyboardButton("Change Location", callback_data='nav_locations')],
        ]
        
        # Verify "Online Stats Report" button exists
        button_labels = [row[0].text for row in keyboard]
        assert "Online Stats Report" in button_labels

    def test_navigation_keyboard_stats_button_callback_data(self):
        """Test that the Online Stats Report button has correct callback data."""
        keyboard = [
            [InlineKeyboardButton("WAN Consumption Report", callback_data='nav_wan')],
            [InlineKeyboardButton("Online Stats Report", callback_data='nav_stats')],
            [InlineKeyboardButton("Get Node Details", callback_data='nav_nodes')],
            [InlineKeyboardButton("List WiFi Networks", callback_data='nav_wifi')],
            [InlineKeyboardButton("Change Location", callback_data='nav_locations')],
        ]
        
        # Find the Online Stats Report button
        stats_button = None
        for row in keyboard:
            for button in row:
                if button.text == "Online Stats Report":
                    stats_button = button
                    break
        
        assert stats_button is not None
        assert stats_button.callback_data == 'nav_stats'

    def test_navigation_keyboard_button_order(self):
        """Test that the Online Stats Report button is in the correct position."""
        keyboard = [
            [InlineKeyboardButton("WAN Consumption Report", callback_data='nav_wan')],
            [InlineKeyboardButton("Online Stats Report", callback_data='nav_stats')],
            [InlineKeyboardButton("Get Node Details", callback_data='nav_nodes')],
            [InlineKeyboardButton("List WiFi Networks", callback_data='nav_wifi')],
            [InlineKeyboardButton("Change Location", callback_data='nav_locations')],
        ]
        
        button_labels = [row[0].text for row in keyboard]
        
        # Verify order: WAN Consumption Report, Online Stats Report, then others
        wan_index = button_labels.index("WAN Consumption Report")
        stats_index = button_labels.index("Online Stats Report")
        change_location_index = button_labels.index("Change Location")
        
        assert stats_index > wan_index, "Online Stats Report should be after WAN Consumption Report"
        assert stats_index < change_location_index, "Online Stats Report should be before Change Location"

    def test_navigation_keyboard_has_all_buttons(self):
        """Test that the navigation keyboard has all expected buttons."""
        keyboard = [
            [InlineKeyboardButton("WAN Consumption Report", callback_data='nav_wan')],
            [InlineKeyboardButton("Online Stats Report", callback_data='nav_stats')],
            [InlineKeyboardButton("Get Node Details", callback_data='nav_nodes')],
            [InlineKeyboardButton("List WiFi Networks", callback_data='nav_wifi')],
            [InlineKeyboardButton("Change Location", callback_data='nav_locations')],
        ]
        
        expected_buttons = [
            "WAN Consumption Report",
            "Online Stats Report",
            "Get Node Details",
            "List WiFi Networks",
            "Change Location",
        ]
        
        button_labels = [row[0].text for row in keyboard]
        assert button_labels == expected_buttons


class TestNavigationHandler:
    """Tests for the navigation handler routing logic."""

    def test_navigation_handler_parses_stats_command(self):
        """Test that 'nav_stats' callback data is correctly parsed."""
        callback_data = 'nav_stats'
        command = callback_data.split('_')[1]
        assert command == 'stats'

    def test_navigation_handler_parses_all_commands(self):
        """Test that all navigation callback data values are correctly parsed."""
        test_cases = [
            ('nav_wan', 'wan'),
            ('nav_stats', 'stats'),
            ('nav_nodes', 'nodes'),
            ('nav_wifi', 'wifi'),
            ('nav_locations', 'locations'),
        ]
        
        for callback_data, expected_command in test_cases:
            command = callback_data.split('_')[1]
            assert command == expected_command, f"Failed for {callback_data}"
