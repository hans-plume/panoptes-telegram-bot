"""
Stats Formatter

Functions to format online statistics data for Telegram messages.
"""

from typing import Dict, Any


def format_progress_bar(percentage: float, length: int = 8) -> str:
    """
    Create a visual progress bar from a percentage.

    Args:
        percentage: Value from 0.0 to 100.0.
        length: Number of characters in the bar.

    Returns:
        Progress bar string (e.g., "████████" for 100%).
    """
    filled = int((percentage / 100) * length)
    bar = "█" * filled + "░" * (length - filled)
    return bar


def get_status_emoji(status_label: str) -> str:
    """
    Get the appropriate emoji for a status label.

    Args:
        status_label: Status string (Excellent, Good, Fair, Poor, Critical).

    Returns:
        Status emoji.
    """
    emoji_map = {
        "Excellent": "✅",
        "Good": "✅",
        "Fair": "🟡",
        "Poor": "🟠",
        "Critical": "🔴",
    }
    return emoji_map.get(status_label, "❓")


def get_trend_emoji(trend: str) -> str:
    """
    Get the appropriate emoji for a trend.

    Args:
        trend: Trend string (improving, stable, declining).

    Returns:
        Trend emoji with label.
    """
    trend_map = {
        "improving": "↗️ Improving",
        "stable": "➡️ Stable",
        "declining": "↘️ Declining",
    }
    return trend_map.get(trend, "➡️ Stable")


def truncate_text(text: str, max_length: int) -> str:
    """
    Truncate text to max length with ellipsis if needed.

    Args:
        text: Text to truncate.
        max_length: Maximum length of the result.

    Returns:
        Truncated text with ellipsis if needed.
    """
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    return text[: max_length - 1] + "…"


def format_status_box(stats_data: Dict[str, Any]) -> str:
    """
    Format the status summary box.

    Args:
        stats_data: Processed statistics dictionary.

    Returns:
        Formatted status box string.
    """
    status_label = stats_data.get("status_label", "Unknown")
    time_range_label = stats_data.get("time_range_label", "")
    trend = stats_data.get("trend", "stable")
    incidents = stats_data.get("incidents", 0)

    status_emoji = get_status_emoji(status_label)
    trend_display = get_trend_emoji(trend)

    # Truncate values to fit in box layout
    status_display = truncate_text(status_label, 15)
    time_display = truncate_text(time_range_label, 22)
    trend_truncated = truncate_text(trend_display, 14)
    incident_display = str(incidents)[:13]

    lines = [
        "┌──────────────────────────────┐",
        f"│  {status_emoji} Status: {status_display:<15} │",
        f"│  ⏱️  {time_display:<22} │",
        f"│  📈 Trend: {trend_truncated:<14} │",
        f"│  🔔 Incidents: {incident_display:<13} │",
        "└──────────────────────────────┘",
    ]
    return "\n".join(lines)


def format_breakdown(stats_data: Dict[str, Any]) -> str:
    """
    Format the detailed breakdown section.

    Args:
        stats_data: Processed statistics dictionary.

    Returns:
        Formatted breakdown string.
    """
    online = stats_data.get("online_count", 0)
    intermittent = stats_data.get("intermittent_count", 0)
    offline = stats_data.get("offline_count", 0)
    total = stats_data.get("total_count", 0)

    if total == 0:
        return "📊 DETAILED BREAKDOWN:\n   No data available"

    online_pct = (online / total) * 100
    intermittent_pct = (intermittent / total) * 100
    offline_pct = (offline / total) * 100

    lines = [
        "📊 DETAILED BREAKDOWN:",
        f"   🟢 Online:      {online:>4} ({online_pct:>5.1f}%)",
        f"   🟡 Intermittent:{intermittent:>4} ({intermittent_pct:>5.1f}%)",
        f"   🔴 Offline:     {offline:>4} ({offline_pct:>5.1f}%)",
    ]
    return "\n".join(lines)


def format_online_stats_message(
    location_name: str, stats_data: Dict[str, Any]
) -> str:
    """
    Main formatting function for online stats Telegram message.

    Creates a visually appealing dashboard-style message.

    Args:
        location_name: Name of the location.
        stats_data: Processed statistics dictionary.

    Returns:
        Formatted message string ready for Telegram.
    """
    uptime = stats_data.get("uptime_percentage", 0.0)
    progress_bar = format_progress_bar(uptime)

    # Truncate location name to fit in header box
    display_name = truncate_text(location_name, 22)

    # Header
    header = (
        "╭──────────────────────────────╮\n"
        f"│   🏢 {display_name:<22} │\n"
        "│   Connection Status Report   │\n"
        "╰──────────────────────────────╯"
    )

    # Uptime display
    uptime_display = (
        "\n         ╭─────────────╮\n"
        f"         │  📊 {uptime:>5.1f}%  │\n"
        f"         │   {progress_bar}  │\n"
        "         │   ONLINE    │\n"
        "         ╰─────────────╯\n"
    )

    # Status box
    status_box = format_status_box(stats_data)

    # Breakdown
    breakdown = format_breakdown(stats_data)

    # Combine all parts
    message = f"{header}\n{uptime_display}\n{status_box}\n\n{breakdown}"

    return message


def get_time_range_keyboard_text() -> str:
    """
    Get the text to display above the time range buttons.

    Returns:
        Button instruction text.
    """
    return "Select a time range to view:"
