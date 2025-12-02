"""
Online Stats API Client

This module provides functions to fetch location online statistics from the Plume Cloud API.
"""

import logging
from typing import Optional

from plume_api_client import plume_request, PlumeAPIError

logger = logging.getLogger(__name__)


async def get_location_online_stats(
    user_id: int,
    customer_id: str,
    location_id: str,
    granularity: str = "days",
    limit: int = 7,
) -> dict:
    """
    Fetch online statistics for a specific location.

    This function calls the Plume Cloud API to retrieve connection status
    history for a given location.

    Args:
        user_id: The Telegram user ID for authentication.
        customer_id: The Plume customer ID.
        location_id: The location ID to get stats for.
        granularity: Time granularity - 'days' or 'hours'.
        limit: Number of periods to collect.

    Returns:
        Dictionary containing:
            - statsDateRange: Start and end timestamps
            - locationState: Array of time-series data with timestamp and value

    Raises:
        PlumeAPIError: If the API request fails.
    """
    logger.info(
        "Fetching online stats for location %s (granularity=%s, limit=%d)",
        location_id,
        granularity,
        limit,
    )

    try:
        response = await plume_request(
            user_id=user_id,
            method="GET",
            endpoint=f"Customers/{customer_id}/locations/{location_id}/onlineStats",
            params={"granularity": granularity, "limit": limit},
            use_reports_api=True,
        )
        logger.info("Successfully fetched online stats for location %s", location_id)
        return response
    except PlumeAPIError:
        logger.error("Failed to fetch online stats for location %s", location_id)
        raise
