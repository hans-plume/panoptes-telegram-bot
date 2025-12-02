"""
Stats Formatter Module

Functions for formatting online stats data into visually appealing
Telegram messages with Unicode graphics.
"""

from typing import Optional
from src.models.online_stats_model import UptimeMetrics


def format_progress_bar(percentage: float, bar_length: int = 8) -> str:
    """
    Create a visual progress bar using block characters.

    Args:
        percentage: Value between 0 and 100.
        bar_length: Number of bar segments.

    Returns:
        String representation of progress bar.
    """
    filled = int((percentage / 100) * bar_length)
    empty = bar_length - filled
    return "█" * filled + "░" * empty


def format_status_box(metrics: UptimeMetrics) -> str:
    """
    Format the status summary box section.

    Args:
        metrics: UptimeMetrics object with calculated values.

    Returns:
        Formatted status box string.
    """
    # Map status to emoji
    status_emoji = {
        "Excellent": "✅",
        "Good": "✅",
        "Fair": "🟡",
        "Poor": "⚠️",
        "Critical": "🔴",
    }

    # Map trend to emoji
    trend_emoji = {
        "improving": "↗️",
        "stable": "➡️",
        "declining": "↘️",
    }

    emoji = status_emoji.get(metrics.status_label, "❓")
    trend_icon = trend_emoji.get(metrics.trend, "➡️")
    trend_label = metrics.trend.capitalize()

    # Count total incidents
    total_incidents = 0
    for incident in metrics.incidents:
        total_incidents += len(incident.get("entries", []))

    lines = [
        "┌──────────────────────────────┐",
        f"│  {emoji} Status: {metrics.status_label:<16} │",
        f"│  ⏱️  {metrics.time_range_label:<22} │",
        f"│  📈 Trend: {trend_icon} {trend_label:<14} │",
        f"│  🔔 Incidents: {total_incidents:<14} │",
        "└──────────────────────────────┘",
    ]
    return "\n".join(lines)


def format_breakdown(metrics: UptimeMetrics) -> str:
    """
    Format the detailed breakdown section.

    Args:
        metrics: UptimeMetrics object with calculated values.

    Returns:
        Formatted breakdown string.
    """
    total = metrics.total_count if metrics.total_count > 0 else 1

    online_pct = (metrics.online_count / total) * 100
    intermittent_pct = (metrics.intermittent_count / total) * 100
    offline_pct = (metrics.offline_count / total) * 100

    lines = [
        "📊 DETAILED BREAKDOWN:",
        f"   🟢 Online:       {metrics.online_count:>4} ({online_pct:.1f}%)",
        f"   🟡 Intermittent: {metrics.intermittent_count:>4} ({intermittent_pct:.1f}%)",
        f"   🔴 Offline:      {metrics.offline_count:>4} ({offline_pct:.1f}%)",
    ]
    return "\n".join(lines)


def format_online_stats_message(
    location_name: str,
    metrics: UptimeMetrics,
) -> str:
    """
    Main formatting function for online stats Telegram message.

    Args:
        location_name: Name of the location.
        metrics: UptimeMetrics object with calculated values.

    Returns:
        Fully formatted Telegram message string.
    """
    progress_bar = format_progress_bar(metrics.uptime_percentage)

    # Header section
    header = [
        "╭──────────────────────────────╮",
        f"│   🏢 {location_name[:20]:<21} │",
        "│   Connection Status Report   │",
        "╰──────────────────────────────╯",
    ]

    # Circular progress section
    progress_section = [
        "",
        "         ╭─────────────╮",
        f"         │  📊 {metrics.uptime_percentage:>5.1f}%  │",
        f"         │   {progress_bar}  │",
        "         │   ONLINE    │",
        "         ╰─────────────╯",
        "",
    ]

    # Status box
    status_box = format_status_box(metrics)

    # Breakdown
    breakdown = format_breakdown(metrics)

    # Combine all sections
    message_parts = [
        "\n".join(header),
        "\n".join(progress_section),
        status_box,
        "",
        breakdown,
    ]

    return "\n".join(message_parts)


def get_time_range_keyboard_text(selected: str) -> list:
    """
    Get keyboard button text with selection indicator.

    Args:
        selected: Currently selected time range ('3h', '24h', '7d').

    Returns:
        List of button texts for 3h, 24h, 7d buttons.
    """
    buttons = {
        "3h": "3️⃣ Hrs",
        "24h": "24️⃣ Hrs",
        "7d": "7️⃣ Days",
    }

    result = []
    for key, text in buttons.items():
        if key == selected:
            result.append(f"✓ {text}")
        else:
            result.append(text)

    return result
