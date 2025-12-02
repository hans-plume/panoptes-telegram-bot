"""Tests for online stats functionality."""

import pytest
from src.utils.stats_processor import (
    calculate_uptime_percentage,
    detect_incidents,
    analyze_connectivity_trend,
    get_status_label,
    process_online_stats,
)
from src.utils.stats_formatter import (
    format_progress_bar,
    format_status_box,
    format_breakdown,
    format_online_stats_message,
)
from src.models.online_stats_model import UptimeMetrics


class TestUptimeCalculation:
    """Tests for uptime percentage calculation."""

    def test_all_online(self):
        """Test 100% uptime when all entries are online."""
        location_state = [
            {"timestamp": "2025-11-24T23:00:00.000Z", "value": "online"},
            {"timestamp": "2025-11-25T00:00:00.000Z", "value": "online"},
            {"timestamp": "2025-11-25T01:00:00.000Z", "value": "online"},
        ]
        assert calculate_uptime_percentage(location_state) == 100.0

    def test_all_offline(self):
        """Test 0% uptime when all entries are offline."""
        location_state = [
            {"timestamp": "2025-11-24T23:00:00.000Z", "value": "offline"},
            {"timestamp": "2025-11-25T00:00:00.000Z", "value": "offline"},
        ]
        assert calculate_uptime_percentage(location_state) == 0.0

    def test_mixed_states(self):
        """Test mixed online/offline states."""
        location_state = [
            {"timestamp": "2025-11-24T23:00:00.000Z", "value": "online"},
            {"timestamp": "2025-11-25T00:00:00.000Z", "value": "offline"},
            {"timestamp": "2025-11-25T01:00:00.000Z", "value": "online"},
            {"timestamp": "2025-11-25T02:00:00.000Z", "value": "intermittent"},
        ]
        # 2 online out of 4 = 50%
        assert calculate_uptime_percentage(location_state) == 50.0

    def test_empty_state(self):
        """Test empty location state returns 0."""
        assert calculate_uptime_percentage([]) == 0.0

    def test_case_insensitive(self):
        """Test that status values are case-insensitive."""
        location_state = [
            {"value": "ONLINE"},
            {"value": "Online"},
            {"value": "online"},
        ]
        assert calculate_uptime_percentage(location_state) == 100.0


class TestIncidentDetection:
    """Tests for incident detection."""

    def test_no_incidents(self):
        """Test no incidents when all online."""
        location_state = [
            {"timestamp": "2025-11-24T23:00:00.000Z", "value": "online"},
            {"timestamp": "2025-11-25T00:00:00.000Z", "value": "online"},
        ]
        result = detect_incidents(location_state)
        assert result["total_incidents"] == 0
        assert len(result["offline_incidents"]) == 0
        assert len(result["intermittent_incidents"]) == 0

    def test_offline_incidents(self):
        """Test detection of offline incidents."""
        location_state = [
            {"timestamp": "2025-11-24T23:00:00.000Z", "value": "online"},
            {"timestamp": "2025-11-25T00:00:00.000Z", "value": "offline"},
            {"timestamp": "2025-11-25T01:00:00.000Z", "value": "offline"},
        ]
        result = detect_incidents(location_state)
        assert result["total_incidents"] == 2
        assert len(result["offline_incidents"]) == 2

    def test_intermittent_incidents(self):
        """Test detection of intermittent incidents."""
        location_state = [
            {"timestamp": "2025-11-24T23:00:00.000Z", "value": "intermittent"},
            {"timestamp": "2025-11-25T00:00:00.000Z", "value": "online"},
        ]
        result = detect_incidents(location_state)
        assert result["total_incidents"] == 1
        assert len(result["intermittent_incidents"]) == 1


class TestTrendAnalysis:
    """Tests for connectivity trend analysis."""

    def test_stable_trend(self):
        """Test stable trend when no significant change."""
        location_state = [
            {"value": "online"} for _ in range(10)
        ]
        assert analyze_connectivity_trend(location_state) == "stable"

    def test_improving_trend(self):
        """Test improving trend when second half is better."""
        location_state = (
            [{"value": "offline"} for _ in range(5)] +
            [{"value": "online"} for _ in range(5)]
        )
        assert analyze_connectivity_trend(location_state) == "improving"

    def test_declining_trend(self):
        """Test declining trend when second half is worse."""
        location_state = (
            [{"value": "online"} for _ in range(5)] +
            [{"value": "offline"} for _ in range(5)]
        )
        assert analyze_connectivity_trend(location_state) == "declining"

    def test_insufficient_data(self):
        """Test returns stable when insufficient data."""
        location_state = [{"value": "online"}, {"value": "offline"}]
        assert analyze_connectivity_trend(location_state) == "stable"


class TestStatusLabel:
    """Tests for status label mapping."""

    def test_excellent_status(self):
        assert get_status_label(99.9) == "Excellent"
        assert get_status_label(100) == "Excellent"

    def test_good_status(self):
        assert get_status_label(98.5) == "Good"
        assert get_status_label(99.0) == "Good"

    def test_fair_status(self):
        assert get_status_label(95.0) == "Fair"
        assert get_status_label(97.9) == "Fair"

    def test_poor_status(self):
        assert get_status_label(90.0) == "Poor"
        assert get_status_label(94.9) == "Poor"

    def test_critical_status(self):
        assert get_status_label(50.0) == "Critical"
        assert get_status_label(0) == "Critical"


class TestProgressBar:
    """Tests for progress bar formatting."""

    def test_full_bar(self):
        """Test 100% fills all segments."""
        bar = format_progress_bar(100, bar_length=8)
        assert bar == "████████"

    def test_empty_bar(self):
        """Test 0% is all empty."""
        bar = format_progress_bar(0, bar_length=8)
        assert bar == "░░░░░░░░"

    def test_half_bar(self):
        """Test 50% fills half."""
        bar = format_progress_bar(50, bar_length=8)
        assert bar == "████░░░░"


class TestProcessOnlineStats:
    """Tests for the main processing function."""

    def test_process_sample_data(self):
        """Test processing sample API response data."""
        stats_data = {
            "statsDateRange": {
                "start": "2025-11-24T22:51:20.379Z",
                "end": "2025-12-01T22:51:20.379Z"
            },
            "locationState": [
                {"timestamp": "2025-11-24T23:00:00.000Z", "value": "online"},
                {"timestamp": "2025-11-25T00:00:00.000Z", "value": "online"},
                {"timestamp": "2025-11-25T01:00:00.000Z", "value": "offline"},
                {"timestamp": "2025-11-25T02:00:00.000Z", "value": "online"},
            ]
        }

        result = process_online_stats(stats_data, "days", 7)

        assert isinstance(result, UptimeMetrics)
        assert result.uptime_percentage == 75.0
        assert result.online_count == 3
        assert result.offline_count == 1
        assert result.total_count == 4
        assert result.time_range_label == "Last 7 Days"

    def test_process_empty_data(self):
        """Test processing empty data."""
        stats_data = {"locationState": []}
        result = process_online_stats(stats_data, "hours", 3)

        assert result.uptime_percentage == 0.0
        assert result.total_count == 0
        assert result.time_range_label == "Last 3 Hours"


class TestMessageFormatting:
    """Tests for message formatting."""

    def test_format_status_box(self):
        """Test status box formatting."""
        metrics = UptimeMetrics(
            uptime_percentage=99.8,
            online_count=100,
            offline_count=0,
            intermittent_count=1,
            total_count=101,
            status_label="Excellent",
            trend="stable",
            time_range_label="Last 7 Days",
            incidents=[
                {"type": "offline", "entries": []},
                {"type": "intermittent", "entries": [{"timestamp": "test"}]},
            ],
        )

        box = format_status_box(metrics)
        assert "Excellent" in box
        assert "Last 7 Days" in box
        assert "Stable" in box
        assert "1" in box  # 1 incident

    def test_format_breakdown(self):
        """Test breakdown formatting."""
        metrics = UptimeMetrics(
            uptime_percentage=75.0,
            online_count=3,
            offline_count=1,
            intermittent_count=0,
            total_count=4,
        )

        breakdown = format_breakdown(metrics)
        assert "Online:" in breakdown
        assert "Offline:" in breakdown
        assert "75.0%" in breakdown

    def test_format_full_message(self):
        """Test full message formatting."""
        metrics = UptimeMetrics(
            uptime_percentage=99.8,
            online_count=672,
            offline_count=0,
            intermittent_count=1,
            total_count=673,
            status_label="Excellent",
            trend="stable",
            time_range_label="Last 7 Days",
            incidents=[
                {"type": "offline", "entries": []},
                {"type": "intermittent", "entries": [{}]},
            ],
        )

        message = format_online_stats_message("Downtown Store", metrics)

        assert "Downtown Store" in message
        assert "99.8%" in message
        assert "ONLINE" in message
        assert "Excellent" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
