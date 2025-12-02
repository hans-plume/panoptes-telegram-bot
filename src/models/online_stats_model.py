"""
Online Stats Data Models

Pydantic models for the online statistics API response and calculated metrics.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class StatsDateRange(BaseModel):
    """Time range metadata for stats data."""

    start: datetime = Field(..., description="Start timestamp of the stats period")
    end: datetime = Field(..., description="End timestamp of the stats period")


class LocationStateEntry(BaseModel):
    """Individual status entry with timestamp and value."""

    timestamp: datetime = Field(..., description="Timestamp of the status entry")
    value: str = Field(..., description="Status value: 'online', 'offline', or 'intermittent'")


class OnlineStatsResponse(BaseModel):
    """Complete API response model for online stats."""

    statsDateRange: StatsDateRange = Field(..., description="Time range of the stats")
    locationState: List[LocationStateEntry] = Field(
        default_factory=list, description="Array of time-series status data"
    )


class UptimeMetrics(BaseModel):
    """Calculated uptime metrics from location state data."""

    uptime_percentage: float = Field(
        0.0, ge=0, le=100, description="Uptime percentage (0-100)"
    )
    online_count: int = Field(0, ge=0, description="Number of online data points")
    offline_count: int = Field(0, ge=0, description="Number of offline data points")
    intermittent_count: int = Field(
        0, ge=0, description="Number of intermittent data points"
    )
    total_count: int = Field(0, ge=0, description="Total number of data points")
    incidents: List[dict] = Field(
        default_factory=list,
        description="List of incidents (offline/intermittent periods)",
    )
    trend: str = Field("stable", description="Connectivity trend: improving/stable/declining")
    status_label: str = Field("Unknown", description="Human-readable status label")
    time_range_label: str = Field("", description="Human-readable time range label")
