"""
Online Stats Data Models

Pydantic models for the location online statistics API response.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class StatsDateRange(BaseModel):
    """Time range for the statistics data."""

    start: datetime = Field(..., description="Start timestamp of the stats range")
    end: datetime = Field(..., description="End timestamp of the stats range")


class LocationStateEntry(BaseModel):
    """Individual status entry with timestamp and value."""

    timestamp: datetime = Field(..., description="Timestamp of the status entry")
    value: str = Field(..., description="Connection state value (online/offline)")


class OnlineStatsResponse(BaseModel):
    """Complete API response model for online statistics."""

    statsDateRange: StatsDateRange = Field(
        ..., description="Date range for the statistics"
    )
    locationState: List[LocationStateEntry] = Field(
        default_factory=list, description="Array of location state entries"
    )


class UptimeMetrics(BaseModel):
    """Calculated uptime metrics from location state data."""

    uptime_percentage: float = Field(
        default=0.0, description="Percentage of time online"
    )
    online_count: int = Field(default=0, description="Number of online data points")
    offline_count: int = Field(default=0, description="Number of offline data points")
    intermittent_count: int = Field(
        default=0, description="Number of intermittent/degraded data points"
    )
    total_count: int = Field(default=0, description="Total number of data points")
    incidents: int = Field(default=0, description="Number of offline incidents")
    trend: str = Field(default="stable", description="Connectivity trend")
    status_label: str = Field(default="Unknown", description="Human-readable status")
    time_range_label: str = Field(
        default="", description="Human-readable time range label"
    )
