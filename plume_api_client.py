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

async def plume_request(user_id: int, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> dict:
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
        params={"limit": 100} # Get up to 100 customers
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

# ============ SERVICE HEALTH ANALYSIS ============

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

        pod_info = {
            "name": nickname,
            "connection_state": node.get("connectionState", "unknown"),
            "health_status": health_status,
            "backhaul_type": node.get("backhaulType", "unknown"),
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
