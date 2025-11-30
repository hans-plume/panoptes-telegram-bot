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

# ============ HEALTH STATUS CONSTANTS ============
HEALTH_STATUS_POOR = "poor"
HEALTH_STATUS_FAIR = "fair"
WARNING_HEALTH_STATUSES = [HEALTH_STATUS_POOR, HEALTH_STATUS_FAIR]

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

# ============ SERVICE HEALTH ANALYSIS ============

def analyze_location_health(location_data: dict, nodes: list) -> dict:
    """
    Comprehensive health analysis for a location.
    
    Extracts:
    - Individual pod health status (poor/fair/excellent)
    - Active alerts on each pod
    - Backhaul connection type (Ethernet/WiFi)
    - ISP speed test results from location data
    
    A location is considered "online" if at least one gateway POD is connected.
    """
    health_report = {
        "online": False, 
        "issues": [], 
        "warnings": [], 
        "disconnected_nodes": [], 
        "pods_with_warnings": [],
        "summary": "",
        "connected_devices": 0,
        "pods": [],  # Detailed pod information
        "speed_test": {
            "download": None,
            "upload": None,
            "latency": None
        }
    }
    
    # Extract ISP speed test results from location data
    isp_speed_test = location_data.get("ispSpeedTestResult", {})
    if isp_speed_test:
        health_report["speed_test"]["download"] = isp_speed_test.get("download")
        health_report["speed_test"]["upload"] = isp_speed_test.get("upload")
        health_report["speed_test"]["latency"] = isp_speed_test.get("latency")
    
    connected_gateways = 0
    total_connected_devices = 0

    if isinstance(nodes, list):
        for node in nodes:
            backhaul_type = node.get('backhaulType', 'unknown')
            is_gateway = backhaul_type == 'ethernet'
            connection_state = node.get("connectionState", "").lower()
            is_connected = connection_state == "connected"
            
            nickname = node.get("nickname", node.get("id", "Unknown Pod"))
            
            # Extract health status from node data (with null safety)
            health_data = node.get("health") or {}
            health_status = health_data.get("status", "unknown").lower()
            
            # Extract active alerts from node
            alerts = node.get("alerts", [])
            active_alerts = []
            for alert in alerts:
                if isinstance(alert, dict):
                    alert_type = alert.get("type", alert.get("name", "Unknown Alert"))
                    active_alerts.append(alert_type)
                elif isinstance(alert, str):
                    active_alerts.append(alert)
            
            # Build detailed pod info
            pod_info = {
                "nickname": nickname,
                "id": node.get("id", "Unknown"),
                "connection_state": connection_state,
                "is_connected": is_connected,
                "backhaul_type": backhaul_type,
                "health_status": health_status,
                "alerts": active_alerts,
                "connected_devices": node.get("connectedDeviceCount", 0)
            }
            health_report["pods"].append(pod_info)

            if is_connected:
                total_connected_devices += node.get("connectedDeviceCount", 0)

            if is_gateway and is_connected:
                connected_gateways += 1
            
            # Track disconnected nodes
            if not is_connected:
                health_report["disconnected_nodes"].append(nickname)
                health_report["issues"].append(f"🔴 Pod '{nickname}' is disconnected")
            # Track pods with health warnings (connected but not healthy)
            elif is_connected and health_status in WARNING_HEALTH_STATUSES:
                health_report["pods_with_warnings"].append(nickname)
                health_report["warnings"].append(f"🟡 Pod '{nickname}' has {health_status} health")
            # Track pods with active alerts
            elif is_connected and active_alerts:
                if nickname not in health_report["pods_with_warnings"]:
                    health_report["pods_with_warnings"].append(nickname)
                for alert in active_alerts:
                    health_report["warnings"].append(f"⚠️ Pod '{nickname}': {alert}")

    health_report["connected_devices"] = total_connected_devices

    # Location is online if at least one gateway is connected.
    if connected_gateways > 0:
        health_report["online"] = True
    
    # Granular summary logic - distinguish between offline pods and health warnings
    if not health_report["online"]:
        health_report["summary"] = "🔴 LOCATION IS OFFLINE - No gateways are connected."
    elif health_report["issues"] and health_report["warnings"]:
        # Both disconnected pods and health warnings
        num_disconnected = len(health_report['disconnected_nodes'])
        num_warnings = len(health_report['pods_with_warnings'])
        health_report["summary"] = f"🔴 {num_disconnected} pod(s) offline, {num_warnings} pod(s) with health warnings"
    elif health_report["issues"]:
        # Only disconnected pods
        num_issues = len(health_report['disconnected_nodes'])
        pod_plural = "pod" if num_issues == 1 else "pods"
        health_report["summary"] = f"🟠 LOCATION ONLINE, but {num_issues} {pod_plural} disconnected"
    elif health_report["warnings"]:
        # Only health warnings (no disconnected pods)
        num_warnings = len(health_report['pods_with_warnings'])
        pod_plural = "pod" if num_warnings == 1 else "pods"
        health_report["summary"] = f"🟡 LOCATION ONLINE, {num_warnings} {pod_plural} with health warnings"
    elif location_data.get("serviceLevel", {}).get("status") != "fullService":
        health_report["summary"] = "🟡 DEGRADED SERVICE"
        health_report["warnings"].append("Service level is not optimal.")
    else:
        health_report["summary"] = "🟢 ALL SYSTEMS OPERATIONAL"

    return health_report
