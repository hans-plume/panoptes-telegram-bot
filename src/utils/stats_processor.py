"""
Stats Processor

Functions to process online statistics API response data.
"""

from typing import List, Dict, Any


def calculate_uptime_percentage(location_state: List[Dict[str, Any]]) -> float:
    """
    Calculate uptime percentage from location state data.

    Args:
        location_state: List of state entries with 'value' field.

    Returns:
        Uptime percentage as a float (0.0 to 100.0).
    """
    if not location_state:
        return 0.0

    online_count = sum(
        1 for entry in location_state if entry.get("value", "").lower() == "online"
    )
    total_count = len(location_state)

    if total_count == 0:
        return 0.0

    return (online_count / total_count) * 100.0


def detect_incidents(location_state: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Find offline and degraded periods in the location state data.

    An incident is defined as a transition to offline or a continuous offline period.

    Args:
        location_state: List of state entries with 'value' and 'timestamp' fields.

    Returns:
        Dictionary with incident count and details.
    """
    if not location_state:
        return {"count": 0, "incidents": []}

    incidents = []
    incident_count = 0
    previous_state = None

    for entry in location_state:
        current_state = entry.get("value", "").lower()
        timestamp = entry.get("timestamp", "")

        # Count transitions to offline as incidents
        if current_state == "offline" and previous_state != "offline":
            incident_count += 1
            incidents.append({"timestamp": timestamp, "state": current_state})

        previous_state = current_state

    return {"count": incident_count, "incidents": incidents}


def analyze_connectivity_trend(location_state: List[Dict[str, Any]]) -> str:
    """
    Determine the connectivity trend from location state data.

    Analyzes the data to determine if connectivity is improving, stable, or declining.

    Args:
        location_state: List of state entries with 'value' field.

    Returns:
        Trend string: "improving", "stable", or "declining".
    """
    if not location_state or len(location_state) < 2:
        return "stable"

    # Split data into two halves and compare online ratios
    mid_point = len(location_state) // 2
    first_half = location_state[:mid_point]
    second_half = location_state[mid_point:]

    def online_ratio(entries: List[Dict[str, Any]]) -> float:
        if not entries:
            return 0.0
        online = sum(1 for e in entries if e.get("value", "").lower() == "online")
        return online / len(entries)

    first_ratio = online_ratio(first_half)
    second_ratio = online_ratio(second_half)

    # Determine trend based on ratio difference
    diff = second_ratio - first_ratio
    if diff > 0.05:  # 5% improvement threshold
        return "improving"
    elif diff < -0.05:  # 5% decline threshold
        return "declining"
    return "stable"


def get_status_label(uptime_percentage: float) -> str:
    """
    Map uptime percentage to a human-readable status label.

    Args:
        uptime_percentage: Uptime as a percentage (0.0 to 100.0).

    Returns:
        Status label string.
    """
    if uptime_percentage >= 99.5:
        return "Excellent"
    elif uptime_percentage >= 98.0:
        return "Good"
    elif uptime_percentage >= 95.0:
        return "Fair"
    elif uptime_percentage >= 90.0:
        return "Poor"
    else:
        return "Critical"


def get_time_range_label(granularity: str, limit: int) -> str:
    """
    Get a human-readable label for the time range.

    Args:
        granularity: 'hours' or 'days'.
        limit: Number of periods.

    Returns:
        Time range label string.
    """
    if granularity == "hours":
        return f"Last {limit} Hour{'s' if limit > 1 else ''}"
    elif granularity == "days":
        if limit == 1:
            return "Last 24 Hours"
        return f"Last {limit} Days"
    return f"Last {limit} {granularity}"


def count_states(location_state: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Count occurrences of each state in the location state data.

    Args:
        location_state: List of state entries with 'value' field.

    Returns:
        Dictionary with counts for online, offline, and intermittent states.
    """
    counts = {"online": 0, "offline": 0, "intermittent": 0}

    for entry in location_state:
        state = entry.get("value", "").lower()
        if state == "online":
            counts["online"] += 1
        elif state == "offline":
            counts["offline"] += 1
        else:
            # Any other state (degraded, intermittent, etc.) counts as intermittent
            counts["intermittent"] += 1

    return counts


def process_online_stats(
    stats_response: Dict[str, Any], granularity: str, limit: int
) -> Dict[str, Any]:
    """
    Process the online stats API response into calculated metrics.

    Args:
        stats_response: Raw API response dictionary.
        granularity: Time granularity ('hours' or 'days').
        limit: Number of periods.

    Returns:
        Dictionary containing all calculated metrics.
    """
    location_state = stats_response.get("locationState", [])

    uptime_percentage = calculate_uptime_percentage(location_state)
    incidents_data = detect_incidents(location_state)
    trend = analyze_connectivity_trend(location_state)
    status_label = get_status_label(uptime_percentage)
    time_range_label = get_time_range_label(granularity, limit)
    state_counts = count_states(location_state)

    return {
        "uptime_percentage": uptime_percentage,
        "online_count": state_counts["online"],
        "offline_count": state_counts["offline"],
        "intermittent_count": state_counts["intermittent"],
        "total_count": len(location_state),
        "incidents": incidents_data["count"],
        "trend": trend,
        "status_label": status_label,
        "time_range_label": time_range_label,
    }
