"""
Plume Cloud API Client Module

This module provides OAuth 2.0 authentication and API wrappers for the Plume Cloud platform.
It handles token management, automatic token refresh, and all API endpoint interactions.
"""

import logging
import httpx
import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta

# ============ CONFIGURATION & LOGGING ============

PLUME_API_BASE = os.getenv("PLUME_API_BASE", "https://piranha-gamma.prod.us-west-2.aws.plumenet.io/api/")
PLUME_REPORTS_BASE = os.getenv("PLUME_REPORTS_BASE", "https://piranha-gamma.prod.us-west-2.aws.plumenet.io/reports/")
PLUME_SSO_URL = "https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token"
PLUME_TIMEOUT = 10  # seconds



logger = logging.getLogger(__name__)

user_auth: Dict[int, Dict] = {}

# ============ EXCEPTIONS ============

class PlumeAPIError(Exception):
    """Base exception for Plume API errors."""
    pass

# ============ AUTHENTICATION MANAGEMENT ============

def set_user_auth(user_id: int, auth_config: Dict) -> None:
    """Store user's OAuth configuration and tokens."""
    user_auth[user_id] = auth_config
    logger.info("Authentication stored for user %s", user_id)


def get_user_auth(user_id: int) -> Optional[Dict]:
    """Retrieve user's OAuth configuration."""
    return user_auth.get(user_id)


def is_oauth_token_valid(user_id: int) -> bool:
    """Check if user has a valid OAuth token."""
    auth = get_user_auth(user_id)
    if not auth or not auth.get("token_expiry"):
        return False
    return datetime.now() < auth["token_expiry"]


async def get_oauth_token(auth_config: Dict) -> Dict:
    """Obtain OAuth token from Plume SSO."""
    try:
        sso_url = auth_config.get("sso_url")
        auth_header = auth_config.get("auth_header")
        partner_id = auth_config.get("partner_id")

        if not all([sso_url, auth_header, partner_id]):
            raise ValueError("Incomplete OAuth configuration")

        headers = {"Authorization": auth_header, "Content-Type": "application/x-www-form-urlencoded"}
        data = {"scope": f"partnerId:{partner_id} role:partnerIdAdmin", "grant_type": "client_credentials"}

        async with httpx.AsyncClient(timeout=PLUME_TIMEOUT) as client:
            resp = await client.post(sso_url, headers=headers, data=data)

        resp.raise_for_status()
        token_data = resp.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            raise PlumeAPIError("No access_token in OAuth response")

        token_expiry = datetime.now() + timedelta(seconds=int(expires_in) - 60)
        logger.info("OAuth token obtained successfully")
        return {"access_token": access_token, "token_expiry": token_expiry}

    except httpx.RequestError as e:
        logger.error("Network error during OAuth: %s", e)
        raise PlumeAPIError("Network error during OAuth authentication") from e
    except Exception as e:
        logger.error("OAuth error: %s", e)
        raise PlumeAPIError(f"An unexpected error occurred during OAuth: {e}") from e

# ============ PLUME API CLIENT ============

async def plume_request(user_id: int, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None, use_reports_api: bool = False) -> dict:
    """Generic function to call the Plume Cloud API."""
    auth_config = get_user_auth(user_id)
    if not auth_config:
        raise PlumeAPIError("No authentication details found. Please use /setup to configure.")

    if not is_oauth_token_valid(user_id):
        logger.info("OAuth token for user %s is expired. Refreshing...", user_id)
        try:
            new_token_data = await get_oauth_token(auth_config)
            auth_config.update(new_token_data)
        except PlumeAPIError as e:
            raise PlumeAPIError("Could not refresh token. Please re-authenticate with /setup.") from e

    token = auth_config.get("access_token")
    
    if use_reports_api:
        api_base = auth_config.get("plume_reports_base", PLUME_REPORTS_BASE)
    else:
        api_base = auth_config.get("plume_api_base", PLUME_API_BASE)
    
    url = f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=PLUME_TIMEOUT) as client:
            resp = await client.request(method=method.upper(), url=url, params=params, json=json_data, headers=headers)
        
        if 400 <= resp.status_code < 500:
             logger.error("Plume API returned client error %s: %s", resp.status_code, resp.text[:300])
             raise PlumeAPIError(f"Plume API client error (status {resp.status_code}). Check your request.")
        
        resp.raise_for_status()
        return resp.json()

    except httpx.TimeoutException as e:
        raise PlumeAPIError("Request timed out. Plume Cloud is taking too long.") from e
    except httpx.RequestError as e:
        raise PlumeAPIError("Network error while contacting Plume Cloud.") from e

# ============ BUSINESS LOGIC / PLUME API WRAPPERS ============

async def get_customers(user_id: int) -> list:
    """
    Get all customers accessible by the partner.
    Endpoint: GET /Customers
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint="Customers",
        params={"limit": 100}
    )

async def get_locations_for_customer(user_id: int, customer_id: str) -> list:
    """
    Get all locations for a specific customer.
    Endpoint: GET /Customers/{customerId}/locations
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"Customers/{customer_id}/locations",
        params={"limit": 100}
    )

async def get_nodes_in_location(user_id: int, customer_id: str, location_id: str) -> list:
    """Fetches all nodes (devices) in a specific location for a customer."""
    response_data = await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"Customers/{customer_id}/locations/{location_id}/nodes"
    )
    # The actual list of nodes is under the "nodes" key in the response
    if response_data and isinstance(response_data, dict):
        return response_data.get("nodes", [])
    return []

async def get_location_status(user_id: int, customer_id: str, location_id: str) -> dict:
    """Get location health and status information."""
    return await plume_request(user_id, "GET", f"Customers/{customer_id}/locations/{location_id}")

async def get_wifi_networks(user_id: int, customer_id: str, location_id: str) -> list:
    """Get WiFi networks configured for a location."""
    return await plume_request(user_id, "GET", f"Customers/{customer_id}/locations/{location_id}/wifiNetworks")

async def get_wan_stats(user_id: int, customer_id: str, location_id: str, period: str = "daily") -> dict:
    """
    Get WAN statistics for a specific location.
    Endpoint: GET /reports/Customers/{customerId}/locations/{locationId}/wanStats?period={period}
    
    Args:
        user_id: The user ID
        customer_id: The customer ID
        location_id: The location ID
        period: The time period for stats (default: 'daily')
    
    Returns:
        Dictionary containing WAN stats data with fifteenMins array
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"Customers/{customer_id}/locations/{location_id}/wanStats",
        params={"period": period},
        use_reports_api=True
    )

# ============ SERVICE HEALTH ANALYSIS ============

def format_wan_analysis(analysis: dict) -> str:
    """Formats the WAN consumption analysis dictionary into a user-friendly report."""
    report_parts = ["📊 *WAN Link Consumption Report (Last 24 Hours)*\n"]
    
    # Peak Capacity Section
    peak_rx = analysis.get("peak_rx_mbps", 0)
    peak_tx = analysis.get("peak_tx_mbps", 0)
    peak_rx_time = analysis.get("peak_rx_time", "N/A")
    peak_tx_time = analysis.get("peak_tx_time", "N/A")
    
    report_parts.append(f"🔴 *Peak Capacity*: {peak_rx:.2f} Mbps (RX) at {peak_rx_time}")
    report_parts.append(f"  - Transmit Peak: {peak_tx:.2f} Mbps at {peak_tx_time}")
    
    # Average Usage Section
    avg_rx = analysis.get("avg_rx_mbps", 0)
    avg_tx = analysis.get("avg_tx_mbps", 0)
    report_parts.append("\n📈 *Average Usage*")
    report_parts.append(f"  - RX: {avg_rx:.2f} Mbps")
    report_parts.append(f"  - TX: {avg_tx:.2f} Mbps")
    
    # 95th Percentile Section
    p95_rx = analysis.get("p95_rx_mbps", 0)
    p95_tx = analysis.get("p95_tx_mbps", 0)
    report_parts.append("\n📊 *95th Percentile (Capacity Planning)*")
    report_parts.append(f"  - RX: {p95_rx:.2f} Mbps")
    report_parts.append(f"  - TX: {p95_tx:.2f} Mbps")
    
    # Total Data Transferred Section
    total_rx_mb = analysis.get("total_rx_mbytes", 0)
    total_tx_mb = analysis.get("total_tx_mbytes", 0)
    total_rx_gb = total_rx_mb / 1024
    total_tx_gb = total_tx_mb / 1024
    report_parts.append("\n💾 *Total Data Transferred*")
    report_parts.append(f"  - Download: {total_rx_mb:,.0f} MB ({total_rx_gb:.1f} GB)")
    report_parts.append(f"  - Upload: {total_tx_mb:,.0f} MB ({total_tx_gb:.1f} GB)")
    
    # Peak Activity Windows Section
    peak_windows = analysis.get("peak_activity_windows", [])
    if peak_windows:
        report_parts.append("\n⏰ *Peak Activity Windows*")
        for window in peak_windows:
            report_parts.append(f"  - {window['time_range']}: {window['description']} (avg {window['avg_rx']:.1f} Mbps RX)")
    
    # Data Quality Section
    valid_data_pct = analysis.get("valid_data_percentage", 0)
    report_parts.append(f"\n📊 *Data Quality*: {valid_data_pct:.1f}% valid data points")
    
    # Data Points Info
    data_points = analysis.get("data_points_count", 0)
    report_parts.append(f"📁 *Data Points Analyzed*: {data_points}")
    
    return "\n".join(report_parts)


def analyze_location_health(location_data: dict, nodes: list) -> dict:
    """
    Comprehensive health analysis for a location.
    A location is considered "online" if at least one pod is connected.
    """
    health_report = {
        "online": False,
        "summary": "",
        "issues": [],
        "warnings": [],
        "pod_details": [],
        "total_connected_devices": 0,
    }

    if not isinstance(nodes, list) or not nodes:
        health_report["summary"] = "🔴 LOCATION IS OFFLINE - No pods found for this location."
        return health_report

    connected_pods = 0
    total_connected_devices = 0
    unhealthy_pods = 0

    for node in nodes:
        is_connected = node.get("connectionState", "").lower() == "connected"
        nickname = node.get("defaultName", node.get("id", "Unknown Pod"))
        health = node.get("health") or {}
        health_status = health.get("status", "N/A")

        backhaul_raw = node.get("backhaulType", "unknown")
        backhaul_type = "Mesh" if backhaul_raw.lower() == "wifi" else backhaul_raw
        pod_info = {
            "name": nickname,
            "connection_state": node.get("connectionState", "unknown"),
            "health_status": health_status,
            "backhaul_type": backhaul_type,
            "alerts": [alert.get("type") for alert in node.get("alerts", [])],
        }
        health_report["pod_details"].append(pod_info)

        if is_connected:
            connected_pods += 1
            total_connected_devices += node.get("connectedDeviceCount", 0)

            if health_status.lower() in ["fair", "poor"]:
                unhealthy_pods += 1
                health_report["warnings"].append(f"Pod '{nickname}' has {health_status} health.")
            
            for alert in pod_info["alerts"]:
                health_report["warnings"].append(f"Pod '{nickname}' has an active alert: {alert}")

        else:
            health_report["issues"].append(f"Pod '{nickname}' is disconnected.")

    health_report["total_connected_devices"] = total_connected_devices
    health_report["online"] = connected_pods > 0
    
    # --- NEW SUMMARY LOGIC ---
    if not health_report["online"]:
        health_report["summary"] = "🔴 LOCATION IS OFFLINE - All pods are disconnected."
    elif health_report["issues"]:
        num_issues = len(health_report['issues'])
        pod_plural = "pod" if num_issues == 1 else "pods"
        health_report["summary"] = f"🟠 LOCATION ONLINE, but {num_issues} {pod_plural} are disconnected."
    elif health_report["warnings"]:
        num_warnings = len(health_report["warnings"])
        warning_plural = "issue" if num_warnings == 1 else "issues"
        health_report["summary"] = f"🟡 LOCATION ONLINE, but with {num_warnings} health {warning_plural}."
    elif location_data.get("serviceLevel", {}).get("status") != "fullService":
        health_report["summary"] = "🟡 DEGRADED SERVICE"
        health_report["warnings"].append("Service level is not optimal.")
    else:
        health_report["summary"] = "🟢 ALL SYSTEMS OPERATIONAL"

    return health_report


def analyze_wan_stats(wan_stats_data: dict) -> dict:
    """
    Analyze WAN statistics to generate consumption-focused metrics.
    
    Args:
        wan_stats_data: Dictionary containing 'fifteenMins' array with WAN stats
    
    Returns:
        Dictionary with consumption analytics including peaks, averages,
        95th percentiles, total data transferred, and peak activity windows
    """
    analysis = {
        "peak_rx_mbps": 0,
        "peak_tx_mbps": 0,
        "peak_rx_time": "N/A",
        "peak_tx_time": "N/A",
        "avg_rx_mbps": 0,
        "avg_tx_mbps": 0,
        "p95_rx_mbps": 0,
        "p95_tx_mbps": 0,
        "total_rx_mbytes": 0,
        "total_tx_mbytes": 0,
        "valid_data_percentage": 0,
        "data_points_count": 0,
        "peak_activity_windows": [],
    }
    
    if not wan_stats_data or "fifteenMins" not in wan_stats_data:
        return analysis
    
    data_points = wan_stats_data.get("fifteenMins", [])
    if not data_points:
        return analysis
    
    analysis["data_points_count"] = len(data_points)
    
    # Collect metrics from data points
    rx_mbps_values = []
    tx_mbps_values = []
    null_data_count = 0
    total_rx_mbytes = 0
    total_tx_mbytes = 0
    
    # Track peak times
    peak_rx_mbps = 0
    peak_tx_mbps = 0
    peak_rx_timestamp = None
    peak_tx_timestamp = None
    
    # For activity window detection, store values with timestamps
    hourly_rx_data = {}  # hour -> list of rx values
    
    for data_point in data_points:
        timestamp = data_point.get("timestamp")
        rx_mbytes = data_point.get("rxMbytes")
        tx_mbytes = data_point.get("txMbytes")
        rx_max_mbps = data_point.get("rxMaxMbps")
        tx_max_mbps = data_point.get("txMaxMbps")
        
        # Track null data
        if rx_mbytes is None or tx_mbytes is None or rx_max_mbps is None or tx_max_mbps is None:
            null_data_count += 1
            continue
        
        # Accumulate total data transferred
        total_rx_mbytes += rx_mbytes
        total_tx_mbytes += tx_mbytes
        
        # Collect bandwidth metrics
        rx_mbps_values.append(rx_max_mbps)
        tx_mbps_values.append(tx_max_mbps)
        
        # Track peak RX
        if rx_max_mbps > peak_rx_mbps:
            peak_rx_mbps = rx_max_mbps
            peak_rx_timestamp = timestamp
        
        # Track peak TX
        if tx_max_mbps > peak_tx_mbps:
            peak_tx_mbps = tx_max_mbps
            peak_tx_timestamp = timestamp
        
        # Aggregate hourly data for activity windows
        if timestamp:
            try:
                dt_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour_key = dt_obj.strftime('%H:00')
                if hour_key not in hourly_rx_data:
                    hourly_rx_data[hour_key] = []
                hourly_rx_data[hour_key].append(rx_max_mbps)
            except (ValueError, AttributeError):
                pass
    
    # Calculate statistics
    if rx_mbps_values:
        analysis["avg_rx_mbps"] = sum(rx_mbps_values) / len(rx_mbps_values)
        analysis["peak_rx_mbps"] = peak_rx_mbps
        # Calculate 95th percentile
        sorted_rx = sorted(rx_mbps_values)
        p95_idx = max(0, int(len(sorted_rx) * 0.95))
        analysis["p95_rx_mbps"] = sorted_rx[min(p95_idx, len(sorted_rx) - 1)]
    
    if tx_mbps_values:
        analysis["avg_tx_mbps"] = sum(tx_mbps_values) / len(tx_mbps_values)
        analysis["peak_tx_mbps"] = peak_tx_mbps
        # Calculate 95th percentile
        sorted_tx = sorted(tx_mbps_values)
        p95_idx = max(0, int(len(sorted_tx) * 0.95))
        analysis["p95_tx_mbps"] = sorted_tx[min(p95_idx, len(sorted_tx) - 1)]
    
    # Format peak times
    if peak_rx_timestamp:
        try:
            dt_obj = datetime.fromisoformat(peak_rx_timestamp.replace('Z', '+00:00'))
            analysis["peak_rx_time"] = dt_obj.strftime('%H:%M UTC')
        except (ValueError, AttributeError):
            analysis["peak_rx_time"] = "N/A"
    
    if peak_tx_timestamp:
        try:
            dt_obj = datetime.fromisoformat(peak_tx_timestamp.replace('Z', '+00:00'))
            analysis["peak_tx_time"] = dt_obj.strftime('%H:%M UTC')
        except (ValueError, AttributeError):
            analysis["peak_tx_time"] = "N/A"
    
    # Total data transferred
    analysis["total_rx_mbytes"] = total_rx_mbytes
    analysis["total_tx_mbytes"] = total_tx_mbytes
    
    # Calculate valid data percentage
    if data_points:
        valid_count = len(data_points) - null_data_count
        analysis["valid_data_percentage"] = (valid_count / len(data_points)) * 100
    
    # Detect peak activity windows
    # Calculate average across all hours first
    overall_avg = analysis["avg_rx_mbps"]
    
    # Find hours with above-average traffic (only if we have a meaningful average)
    peak_windows = []
    if overall_avg > 0:
        for hour, values in sorted(hourly_rx_data.items()):
            hour_avg = sum(values) / len(values) if values else 0
            if hour_avg > overall_avg * 1.5:  # 50% above average = high activity
                peak_windows.append({
                    "time_range": f"{hour} UTC",
                    "description": "High activity" if hour_avg > overall_avg * 2 else "Moderate activity",
                    "avg_rx": hour_avg
                })
    
    # Sort by average RX (highest first) and limit to top 3
    peak_windows.sort(key=lambda x: x["avg_rx"], reverse=True)
    analysis["peak_activity_windows"] = peak_windows[:3]
    
    return analysis
