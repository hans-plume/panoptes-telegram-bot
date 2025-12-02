"""Utility functions for data processing and formatting."""

from .stats_processor import (
    calculate_uptime_percentage,
    detect_incidents,
    analyze_connectivity_trend,
    get_status_label,
    process_online_stats,
)
from .stats_formatter import (
    format_online_stats_message,
    format_progress_bar,
    format_status_box,
    format_breakdown,
)

__all__ = [
    "calculate_uptime_percentage",
    "detect_incidents",
    "analyze_connectivity_trend",
    "get_status_label",
    "process_online_stats",
    "format_online_stats_message",
    "format_progress_bar",
    "format_status_box",
    "format_breakdown",
]
