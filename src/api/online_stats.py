"""
Online Stats API Client Module

This module provides API calls to fetch location online statistics
from the Plume Cloud API.
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
    Fetch online statistics for a location from the Plume Cloud API.

    Args:
        user_id: The Telegram user ID for authentication lookup.
        customer_id: The Plume customer ID.
        location_id: The Plume location ID.
        granularity: Time granularity - 'days' or 'hours'.
        limit: Number of periods to collect.

    Returns:
        Dictionary containing:
        - statsDateRange: Start and end timestamps
        - locationState: Array of time-series data with timestamp and value

    Raises:
        PlumeAPIError: If the API request fails.
    """
    if granularity not in ("days", "hours"):
        raise ValueError(f"Invalid granularity: {granularity}. Must be 'days' or 'hours'.")

    if limit < 1:
        raise ValueError(f"Invalid limit: {limit}. Must be at least 1.")

    logger.info(
        "Fetching online stats for location %s (customer %s) with granularity=%s, limit=%d",
        location_id,
        customer_id,
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
