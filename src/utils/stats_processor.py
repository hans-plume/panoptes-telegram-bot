"""
Stats Processor Module

Functions for processing online stats API data to calculate uptime metrics,
detect incidents, and analyze connectivity trends.
"""

from typing import List, Dict, Any
from datetime import datetime
import logging

from src.models.online_stats_model import UptimeMetrics

logger = logging.getLogger(__name__)


def calculate_uptime_percentage(location_state: List[Dict[str, Any]]) -> float:
    """
    Calculate uptime percentage from location state data.

    Args:
        location_state: List of status entries with 'value' key.

    Returns:
        Uptime percentage (0-100) based on 'online' entries.
    """
    if not location_state:
        return 0.0

    total_count = len(location_state)
    online_count = sum(
        1 for entry in location_state if entry.get("value", "").lower() == "online"
    )

    return (online_count / total_count) * 100 if total_count > 0 else 0.0


def detect_incidents(location_state: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Find offline/intermittent periods from location state data.

    Args:
        location_state: List of status entries with 'timestamp' and 'value' keys.

    Returns:
        Dictionary containing:
        - total_incidents: Total number of non-online periods
        - offline_incidents: List of offline period entries
        - intermittent_incidents: List of intermittent period entries
    """
    offline_incidents = []
    intermittent_incidents = []

    for entry in location_state:
        value = entry.get("value", "").lower()
        if value == "offline":
            offline_incidents.append(entry)
        elif value == "intermittent":
            intermittent_incidents.append(entry)

    return {
        "total_incidents": len(offline_incidents) + len(intermittent_incidents),
        "offline_incidents": offline_incidents,
        "intermittent_incidents": intermittent_incidents,
    }


def analyze_connectivity_trend(location_state: List[Dict[str, Any]]) -> str:
    """
    Determine trend in connectivity (improving/stable/declining).

    Analyzes the first half vs second half of the data to determine trend.

    Args:
        location_state: List of status entries with 'value' key.

    Returns:
        Trend string: 'improving', 'stable', or 'declining'.
    """
    if not location_state or len(location_state) < 4:
        return "stable"

    mid_point = len(location_state) // 2
    first_half = location_state[:mid_point]
    second_half = location_state[mid_point:]

    first_half_uptime = calculate_uptime_percentage(first_half)
    second_half_uptime = calculate_uptime_percentage(second_half)

    diff = second_half_uptime - first_half_uptime

    if diff > 5:
        return "improving"
    elif diff < -5:
        return "declining"
    return "stable"


def get_status_label(uptime_percentage: float) -> str:
    """
    Map uptime percentage to human-readable status label.

    Args:
        uptime_percentage: Uptime percentage (0-100).

    Returns:
        Status label string.
    """
    if uptime_percentage >= 99.5:
        return "Excellent"
    elif uptime_percentage >= 98:
        return "Good"
    elif uptime_percentage >= 95:
        return "Fair"
    elif uptime_percentage >= 90:
        return "Poor"
    return "Critical"


def _get_time_range_label(granularity: str, limit: int) -> str:
    """
    Generate human-readable time range label.

    Args:
        granularity: 'days' or 'hours'.
        limit: Number of periods.

    Returns:
        Human-readable time range label.
    """
    if granularity == "hours":
        return f"Last {limit} Hour{'s' if limit > 1 else ''}"
    else:
        if limit == 1:
            return "Last 24 Hours"
        return f"Last {limit} Days"


def process_online_stats(
    stats_data: Dict[str, Any], granularity: str, limit: int
) -> UptimeMetrics:
    """
    Process online stats API response into UptimeMetrics.

    Args:
        stats_data: Raw API response dictionary.
        granularity: Time granularity used ('days' or 'hours').
        limit: Number of periods requested.

    Returns:
        UptimeMetrics object with calculated values.
    """
    location_state = stats_data.get("locationState", [])

    # Count status values
    online_count = 0
    offline_count = 0
    intermittent_count = 0

    for entry in location_state:
        value = entry.get("value", "").lower()
        if value == "online":
            online_count += 1
        elif value == "offline":
            offline_count += 1
        elif value == "intermittent":
            intermittent_count += 1

    total_count = len(location_state)
    uptime_percentage = calculate_uptime_percentage(location_state)
    incidents_data = detect_incidents(location_state)
    trend = analyze_connectivity_trend(location_state)
    status_label = get_status_label(uptime_percentage)
    time_range_label = _get_time_range_label(granularity, limit)

    return UptimeMetrics(
        uptime_percentage=uptime_percentage,
        online_count=online_count,
        offline_count=offline_count,
        intermittent_count=intermittent_count,
        total_count=total_count,
        incidents=[
            {"type": "offline", "entries": incidents_data["offline_incidents"]},
            {"type": "intermittent", "entries": incidents_data["intermittent_incidents"]},
        ],
        trend=trend,
        status_label=status_label,
        time_range_label=time_range_label,
    )
