"""
Plume Cloud Telegram Bot Package

A comprehensive Telegram bot for monitoring Plume Cloud network infrastructure
with OAuth 2.0 authentication, real-time health monitoring, and intelligent
service status reporting.

Requires:
    - python-telegram-bot (with all extras)
    - httpx (for async HTTP requests)

Author: Hans Velez
Nice Suit. John Philips, London. I Have Two Myself - H. Gruber
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Hans Velez"

# Export main components for easy importing
try:
    from plume_api_client import (
        PlumeAPIError,
        get_oauth_token,
        analyze_location_health,
        PLUME_API_BASE,
    )
    __all__ = [
        "__version__",
        "__author__",
        "PlumeAPIError",
        "get_oauth_token",
        "analyze_location_health",
        "PLUME_API_BASE",
    ]
except ImportError:
    # Allow importing package metadata even when dependencies aren't available
    __all__ = ["__version__", "__author__"]
