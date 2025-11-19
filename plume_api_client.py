"""
Plume Cloud API Client Module

This module provides OAuth 2.0 authentication and API wrappers for the Plume Cloud platform.
It handles token management, automatic token refresh, and all API endpoint interactions.

Usage:
    # Initialize and authenticate
    client = PlumeAPIClient(plume_api_base="https://api.plume.com")
    token_data = await client.get_oauth_token(sso_url, auth_header, partner_id)
    
    # Make API calls
    nodes = await client.get_nodes_in_location(user_id, customer_id, location_id)
    health = await client.analyze_location_health(...)
"""

import logging
import httpx
import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta

# ============ CONFIGURATION & LOGGING ============

PLUME_API_BASE = os.getenv("PLUME_API_BASE", "https://piranha-gamma.prod.us-west-2.aws.plumenet.io/api/")
PLUME_SSO_URL = "https://external.sso.plume.com/oauth2/ausc034rgdEZKz75I357/v1/token"
PLUME_TIMEOUT = 10  # seconds

logger = logging.getLogger(__name__)

# User authentication storage (OAuth tokens with expiry)
# In production: use encrypted DB with proper session management
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
    if not auth:
        return False
    
    token_expiry = auth.get("token_expiry")
    if not token_expiry:
        return False
    
    # Check if token expires within next minute
    return datetime.now() < token_expiry


async def get_oauth_token(auth_config: Dict) -> Dict:
    """
    Obtain OAuth token from Plume SSO using client credentials flow.
    
    Args:
        auth_config: Dict with 'sso_url', 'auth_header', 'partner_id'
    
    Returns:
        A dictionary with 'access_token', 'token_expiry', and 'expires_in'.
        
    Raises:
        PlumeAPIError: If OAuth request fails or the response is invalid.
        ValueError: If the provided auth_config is incomplete.
    """
    try:
        sso_url = auth_config.get("sso_url")
        auth_header = auth_config.get("auth_header")
        partner_id = auth_config.get("partner_id")

        if not all([sso_url, auth_header, partner_id]):
            logger.error("Missing OAuth configuration")
            raise ValueError("Incomplete OAuth configuration")

        headers = {
            "Cache-Control": "no-cache",
            "Authorization": auth_header,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "scope": f"partnerId:{partner_id} role:partnerIdAdmin",
            "grant_type": "client_credentials",
        }

        async with httpx.AsyncClient(timeout=PLUME_TIMEOUT) as client:
            resp = await client.post(sso_url, headers=headers, data=data)

        if resp.status_code != 200:
            logger.error("OAuth token request failed: %s - %s", resp.status_code, resp.text[:200])
            raise PlumeAPIError(f"OAuth request failed with status {resp.status_code}")

        token_data = resp.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)  # Default 1 hour

        if not access_token:
            raise PlumeAPIError("No access_token in OAuth response")

        # Calculate token expiry time
        token_expiry = datetime.now() + timedelta(seconds=int(expires_in) - 60)  # Refresh 60s before expiry

        logger.info("OAuth token obtained successfully")
        return {
            "access_token": access_token,
            "token_expiry": token_expiry,
            "expires_in": expires_in,
        }

    except httpx.RequestError as e:
        logger.error("Network error during OAuth: %s", e)
        raise PlumeAPIError("Network error during OAuth authentication") from e
    except Exception as e:
        logger.error("OAuth error: %s", e)
        raise PlumeAPIError(f"An unexpected error occurred during OAuth: {e}") from e


def get_user_token(user_id: int) -> Optional[str]:
    """Get valid OAuth access token for user."""
    if not is_oauth_token_valid(user_id):
        return None
    
    auth = get_user_auth(user_id)
    return auth.get("access_token")


# ============ PLUME API CLIENT ============

async def plume_request(
    user_id: int,
    method: str,
    endpoint: str,
    params: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
) -> dict:
    """
    Call Plume Cloud API for a user.
    
    Args:
        user_id: Telegram user ID
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path (e.g., "/api/Customers/{id}/locations/{id}/nodes")
        params: Optional query parameters
        json_data: Optional JSON body
    
    Returns:
        API response as dictionary
        
    Raises:
        PlumeAPIError: On authentication, network, or API errors
    """
    auth_config = get_user_auth(user_id)
    if not auth_config:
        raise PlumeAPIError(
            "No authentication details found. Please use /auth to configure."
        )

    # --- Automatic Token Refresh Logic ---
    if not is_oauth_token_valid(user_id):
        logger.info("OAuth token for user %s is expired or invalid. Refreshing...", user_id)
        try:
            # Attempt to get a new token using stored credentials
            new_token_data = await get_oauth_token(auth_config)
            auth_config.update(new_token_data)  # Update the stored auth with new token
            logger.info("OAuth token refreshed successfully for user %s", user_id)
        except PlumeAPIError as e:
            logger.error("Failed to refresh OAuth token for user %s: %s", user_id, e)
            # If refresh fails, the original credentials might be bad.
            # Clear the token to prevent retries with a bad token.
            auth_config["access_token"] = None
            auth_config["token_expiry"] = None
            raise PlumeAPIError(
                "Could not refresh token. Please re-authenticate with /auth."
            ) from e

    token = auth_config.get("access_token")
    # --- End of Token Refresh Logic ---
    
    api_base = auth_config.get("plume_api_base", PLUME_API_BASE)
    url = f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=PLUME_TIMEOUT) as client:
            resp = await client.request(
                method=method.upper(), url=url, params=params, json=json_data, headers=headers
            )
    except httpx.TimeoutException as e:
        logger.error("Timeout calling Plume API: %s", e)
        raise PlumeAPIError("Request timed out. Plume Cloud is taking too long to respond.")
    except httpx.RequestError as e:
        logger.error("Network error while calling Plume API: %s", e)
        raise PlumeAPIError("Network error while contacting Plume Cloud")

    if resp.status_code == 401 or resp.status_code == 403:
        # Token likely invalid or expired
        logger.warning(
            "Auth error for user %s: status=%s",
            user_id,
            resp.status_code,
        )
        # Clear invalid token
        auth = get_user_auth(user_id)
        if auth:
            auth["access_token"] = None
        raise PlumeAPIError(
            "Auth failed. Your token may be invalid or expired. Please re-authenticate with /auth."
        )

    if not (200 <= resp.status_code < 300):
        logger.error(
            "Plume API returned status %s: %s",
            resp.status_code,
            resp.text[:300],
        )
        raise PlumeAPIError(
            f"Plume API error (status {resp.status_code}). Try again later or contact support."
        )

    try:
        data = resp.json()
    except ValueError as e:
        logger.error("Invalid JSON from Plume API: %s", e)
        raise PlumeAPIError("Received invalid response format from Plume Cloud")

    return data


# ============ BUSINESS LOGIC / PLUME API WRAPPERS ============

async def get_locations(user_id: int) -> list:
    """
    Get all locations for the user.
    Note: Requires customerId to be obtained first - this is a placeholder.
    In production, use /api/partners/customers/search to find customer.
    """
    try:
        return await plume_request(
            user_id=user_id,
            method="GET",
            endpoint="/api/partners/customers",
            params={"limit": 10}
        )
    except PlumeAPIError:
        return []


async def get_nodes_in_location(user_id: int, customer_id: str, location_id: str) -> list:
    """
    Get all nodes (gateways) in a specific location.
    Endpoint: GET /api/Customers/{customerId}/locations/{locationId}/nodes
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"/api/Customers/{customer_id}/locations/{location_id}/nodes"
    )


async def get_node_details(user_id: int, node_id: str) -> dict:
    """
    Get detailed information about a specific node.
    Endpoint: GET /api/partners/nodes/{nodeId}
    Returns: serialNumber, status, nickname, model, firmwareVersion, connectionState, etc.
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"/api/partners/nodes/{node_id}"
    )


async def get_location_status(user_id: int, customer_id: str, location_id: str) -> dict:
    """
    Get location health and status information.
    Endpoint: GET /api/Customers/{customerId}/locations/{locationId}
    Returns: name, serviceId, speed test averages, connected devices, etc.
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"/api/Customers/{customer_id}/locations/{location_id}"
    )


async def get_wifi_networks(user_id: int, customer_id: str, location_id: str) -> list:
    """
    Get WiFi networks configured for a location.
    Endpoint: GET /api/Customers/{customerId}/locations/{locationId}/wifiNetworks
    Returns: list of WiFi networks with SSIDs and configurations.
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"/api/Customers/{customer_id}/locations/{location_id}/wifiNetworks"
    )


async def get_connected_devices(user_id: int, customer_id: str, location_id: str) -> list:
    """
    Get list of connected devices at a location.
    Endpoint: GET /api/Customers/{customerId}/locations/{locationId}/devices
    Returns: list of devices with MAC, type, connection status, etc.
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"/api/Customers/{customer_id}/locations/{location_id}/devices"
    )


async def get_internet_health(user_id: int, customer_id: str, location_id: str) -> dict:
    """
    Get internet connection health for a location (backhaul status, speed tests).
    Endpoint: GET /api/Customers/{customerId}/locations/{locationId}/backhaul
    Returns: backhaul configuration and connection health metrics.
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"/api/Customers/{customer_id}/locations/{location_id}/backhaul"
    )


async def get_service_level(user_id: int, customer_id: str, location_id: str) -> dict:
    """
    Get service level status for a location.
    Endpoint: GET /api/Customers/{customerId}/locations/{locationId}/serviceLevel
    Returns: service status, health indicators, connection state.
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"/api/Customers/{customer_id}/locations/{location_id}/serviceLevel"
    )


async def get_qoe_stats(user_id: int, customer_id: str, location_id: str) -> dict:
    """
    Get App QoE (Quality of Experience) metrics by traffic class.
    Endpoint: GET /api/Customers/{customerId}/locations/{locationId}/appqoe/AppQoeStatsByTrafficClass
    Returns: QoE metrics for different traffic classes (poor, good, excellent).
    """
    return await plume_request(
        user_id=user_id,
        method="GET",
        endpoint=f"/api/Customers/{customer_id}/locations/{location_id}/appqoe/AppQoeStatsByTrafficClass"
    )


# ============ SERVICE HEALTH ANALYSIS ============

def analyze_location_health(location: dict, service_level: dict, nodes: list, devices: list, qoe: dict) -> dict:
    """
    Comprehensive health analysis for a location.
    Returns a dictionary with human-readable health indicators.
    """
    health_report = {
        "online": False,
        "issues": [],
        "warnings": [],
        "disconnected_nodes": [],
        "disconnected_devices": [],
        "poor_qoe_traffic": [],
        "summary": ""
    }

    # Check if location is online
    location_status = service_level.get("connectionState", "unknown").lower()
    health_report["online"] = location_status == "connected"

    # Check for disconnected nodes/pods
    if isinstance(nodes, list):
        disconnected = []
        for node in nodes:
            if isinstance(node, dict):
                state = node.get("connectionState", node.get("status", "")).lower()
                if state not in ["connected", "online"]:
                    nickname = node.get("nickname", node.get("id", "Unknown Pod"))
                    disconnected.append(nickname)
                    health_report["issues"].append(f"🔴 Pod '{nickname}' is disconnected")
        health_report["disconnected_nodes"] = disconnected

    # Check for disconnected devices
    if isinstance(devices, list):
        disconnected_devs = []
        for device in devices:
            if isinstance(device, dict):
                connected = device.get("connected", device.get("status") == "connected")
                if not connected:
                    mac = device.get("mac", "Unknown")
                    nick = device.get("nickname", mac)
                    disconnected_devs.append(f"{nick} ({mac})")
                    health_report["warnings"].append(f"⚠️ Device '{nick}' is disconnected")
        health_report["disconnected_devices"] = disconnected_devs

    # Check for poor QoE (Quality of Experience)
    if isinstance(qoe, dict):
        traffic_stats = qoe.get("trafficClassStats", [])
        if isinstance(traffic_stats, list):
            for stat in traffic_stats:
                if isinstance(stat, dict):
                    traffic_class = stat.get("trafficClass", "Unknown")
                    health_indicator = stat.get("health", stat.get("qualityIndicator", "healthy"))
                    
                    if health_indicator and "poor" in health_indicator.lower():
                        health_report["poor_qoe_traffic"].append(traffic_class)
                        health_report["warnings"].append(
                            f"⚠️ Poor QoE detected for {traffic_class} traffic"
                        )

    # Generate summary
    if not health_report["online"]:
        health_report["summary"] = "🔴 LOCATION IS OFFLINE - Service is unavailable"
    elif health_report["issues"]:
        health_report["summary"] = "🟠 SERVICE DISRUPTED - Multiple pods are disconnected"
    elif health_report["warnings"]:
        health_report["summary"] = "🟡 DEGRADED SERVICE - Some devices disconnected or poor QoE"
    else:
        health_report["summary"] = "🟢 ALL SYSTEMS OPERATIONAL - No issues detected"

    return health_report
