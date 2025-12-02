"""
Tests for the online stats processing and formatting functionality.
"""

import pytest
from src.utils.stats_processor import (
    calculate_uptime_percentage,
    detect_incidents,
    analyze_connectivity_trend,
    get_status_label,
    get_time_range_label,
    count_states,
    process_online_stats,
)
from src.utils.stats_formatter import (
    format_progress_bar,
    get_status_emoji,
    get_trend_emoji,
    format_status_box,
    format_breakdown,
    format_online_stats_message,
    truncate_text,
)


class TestStatsProcessor:
    """Tests for stats processor functions."""

    def test_calculate_uptime_percentage_all_online(self):
        """Test uptime calculation with all online entries."""
        location_state = [
            {"timestamp": "2025-11-01T00:00:00Z", "value": "online"},
            {"timestamp": "2025-11-01T01:00:00Z", "value": "online"},
            {"timestamp": "2025-11-01T02:00:00Z", "value": "online"},
        ]
        assert calculate_uptime_percentage(location_state) == 100.0

    def test_calculate_uptime_percentage_mixed(self):
        """Test uptime calculation with mixed states."""
        location_state = [
            {"timestamp": "2025-11-01T00:00:00Z", "value": "online"},
            {"timestamp": "2025-11-01T01:00:00Z", "value": "offline"},
            {"timestamp": "2025-11-01T02:00:00Z", "value": "online"},
            {"timestamp": "2025-11-01T03:00:00Z", "value": "online"},
        ]
        assert calculate_uptime_percentage(location_state) == 75.0

    def test_calculate_uptime_percentage_empty(self):
        """Test uptime calculation with empty data."""
        assert calculate_uptime_percentage([]) == 0.0

    def test_detect_incidents_no_incidents(self):
        """Test incident detection with no offline periods."""
        location_state = [
            {"timestamp": "2025-11-01T00:00:00Z", "value": "online"},
            {"timestamp": "2025-11-01T01:00:00Z", "value": "online"},
        ]
        result = detect_incidents(location_state)
        assert result["count"] == 0

    def test_detect_incidents_single_incident(self):
        """Test incident detection with one transition to offline."""
        location_state = [
            {"timestamp": "2025-11-01T00:00:00Z", "value": "online"},
            {"timestamp": "2025-11-01T01:00:00Z", "value": "offline"},
            {"timestamp": "2025-11-01T02:00:00Z", "value": "online"},
        ]
        result = detect_incidents(location_state)
        assert result["count"] == 1

    def test_detect_incidents_multiple_incidents(self):
        """Test incident detection with multiple transitions to offline."""
        location_state = [
            {"timestamp": "2025-11-01T00:00:00Z", "value": "online"},
            {"timestamp": "2025-11-01T01:00:00Z", "value": "offline"},
            {"timestamp": "2025-11-01T02:00:00Z", "value": "online"},
            {"timestamp": "2025-11-01T03:00:00Z", "value": "offline"},
        ]
        result = detect_incidents(location_state)
        assert result["count"] == 2

    def test_analyze_connectivity_trend_stable(self):
        """Test trend analysis with stable connectivity."""
        location_state = [
            {"value": "online"},
            {"value": "online"},
            {"value": "online"},
            {"value": "online"},
        ]
        assert analyze_connectivity_trend(location_state) == "stable"

    def test_analyze_connectivity_trend_improving(self):
        """Test trend analysis with improving connectivity."""
        location_state = [
            {"value": "offline"},
            {"value": "offline"},
            {"value": "online"},
            {"value": "online"},
        ]
        assert analyze_connectivity_trend(location_state) == "improving"

    def test_analyze_connectivity_trend_declining(self):
        """Test trend analysis with declining connectivity."""
        location_state = [
            {"value": "online"},
            {"value": "online"},
            {"value": "offline"},
            {"value": "offline"},
        ]
        assert analyze_connectivity_trend(location_state) == "declining"

    def test_get_status_label_excellent(self):
        """Test status label for excellent uptime."""
        assert get_status_label(99.9) == "Excellent"

    def test_get_status_label_good(self):
        """Test status label for good uptime."""
        assert get_status_label(98.5) == "Good"

    def test_get_status_label_fair(self):
        """Test status label for fair uptime."""
        assert get_status_label(96.0) == "Fair"

    def test_get_status_label_poor(self):
        """Test status label for poor uptime."""
        assert get_status_label(91.0) == "Poor"

    def test_get_status_label_critical(self):
        """Test status label for critical uptime."""
        assert get_status_label(85.0) == "Critical"

    def test_get_time_range_label_hours(self):
        """Test time range label for hours."""
        assert get_time_range_label("hours", 3) == "Last 3 Hours"
        assert get_time_range_label("hours", 1) == "Last 1 Hour"

    def test_get_time_range_label_days(self):
        """Test time range label for days."""
        assert get_time_range_label("days", 1) == "Last 24 Hours"
        assert get_time_range_label("days", 7) == "Last 7 Days"

    def test_count_states(self):
        """Test state counting."""
        location_state = [
            {"value": "online"},
            {"value": "online"},
            {"value": "offline"},
            {"value": "intermittent"},
        ]
        result = count_states(location_state)
        assert result["online"] == 2
        assert result["offline"] == 1
        assert result["intermittent"] == 1

    def test_process_online_stats_complete(self):
        """Test complete stats processing."""
        stats_response = {
            "statsDateRange": {
                "start": "2025-11-01T00:00:00Z",
                "end": "2025-11-08T00:00:00Z",
            },
            "locationState": [
                {"timestamp": "2025-11-01T00:00:00Z", "value": "online"},
                {"timestamp": "2025-11-02T00:00:00Z", "value": "online"},
                {"timestamp": "2025-11-03T00:00:00Z", "value": "offline"},
                {"timestamp": "2025-11-04T00:00:00Z", "value": "online"},
            ],
        }
        result = process_online_stats(stats_response, "days", 7)
        assert result["uptime_percentage"] == 75.0
        assert result["online_count"] == 3
        assert result["offline_count"] == 1
        assert result["total_count"] == 4
        assert result["incidents"] == 1
        assert result["time_range_label"] == "Last 7 Days"


class TestStatsFormatter:
    """Tests for stats formatter functions."""

    def test_truncate_text_short(self):
        """Test truncate text with text shorter than max."""
        assert truncate_text("Hello", 10) == "Hello"

    def test_truncate_text_exact(self):
        """Test truncate text with text exactly at max."""
        assert truncate_text("Hello", 5) == "Hello"

    def test_truncate_text_long(self):
        """Test truncate text with text longer than max."""
        result = truncate_text("Hello World", 8)
        assert result == "Hello W…"
        assert len(result) == 8

    def test_truncate_text_very_short_max(self):
        """Test truncate text with very short max length."""
        assert truncate_text("Hello", 3) == "Hel"

    def test_format_progress_bar_full(self):
        """Test progress bar at 100%."""
        bar = format_progress_bar(100.0)
        assert bar == "████████"

    def test_format_progress_bar_half(self):
        """Test progress bar at 50%."""
        bar = format_progress_bar(50.0)
        assert bar == "████░░░░"

    def test_format_progress_bar_empty(self):
        """Test progress bar at 0%."""
        bar = format_progress_bar(0.0)
        assert bar == "░░░░░░░░"

    def test_get_status_emoji(self):
        """Test status emoji mapping."""
        assert get_status_emoji("Excellent") == "✅"
        assert get_status_emoji("Good") == "✅"
        assert get_status_emoji("Fair") == "🟡"
        assert get_status_emoji("Poor") == "🟠"
        assert get_status_emoji("Critical") == "🔴"
        assert get_status_emoji("Unknown") == "❓"

    def test_get_trend_emoji(self):
        """Test trend emoji mapping."""
        assert get_trend_emoji("improving") == "↗️ Improving"
        assert get_trend_emoji("stable") == "➡️ Stable"
        assert get_trend_emoji("declining") == "↘️ Declining"

    def test_format_status_box(self):
        """Test status box formatting."""
        stats_data = {
            "status_label": "Excellent",
            "time_range_label": "Last 7 Days",
            "trend": "stable",
            "incidents": 1,
        }
        result = format_status_box(stats_data)
        assert "Excellent" in result
        assert "Last 7 Days" in result
        assert "Stable" in result
        assert "1" in result

    def test_format_breakdown(self):
        """Test breakdown formatting."""
        stats_data = {
            "online_count": 100,
            "offline_count": 1,
            "intermittent_count": 0,
            "total_count": 101,
        }
        result = format_breakdown(stats_data)
        assert "Online" in result
        assert "100" in result
        assert "Offline" in result
        assert "1" in result

    def test_format_breakdown_empty(self):
        """Test breakdown formatting with empty data."""
        stats_data = {"total_count": 0}
        result = format_breakdown(stats_data)
        assert "No data available" in result

    def test_format_online_stats_message(self):
        """Test complete message formatting."""
        stats_data = {
            "uptime_percentage": 99.8,
            "online_count": 672,
            "offline_count": 0,
            "intermittent_count": 1,
            "total_count": 673,
            "incidents": 1,
            "trend": "stable",
            "status_label": "Excellent",
            "time_range_label": "Last 7 Days",
        }
        result = format_online_stats_message("Downtown Store", stats_data)
        assert "Downtown Store" in result
        assert "99.8" in result
        assert "Excellent" in result
        assert "ONLINE" in result
