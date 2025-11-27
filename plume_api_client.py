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

async def get_nodes_in_location(user_id: int, customer_id: str, location_id: str) -> list:
    """Get all nodes (gateways) in a specific location."""
    return await plume_request(user_id, "GET", f"Customers/{customer_id}/locations/{location_id}/nodes")

async def get_location_status(user_id: int, customer_id: str, location_id: str) -> dict:
    """Get location health and status information."""
    return await plume_request(user_id, "GET", f"Customers/{customer_id}/locations/{location_id}")

async def get_connected_devices(user_id: int, customer_id: str, location_id: str) -> list:
    """Get list of connected devices at a location."""
    return await plume_request(user_id, "GET", f"Customers/{customer_id}/locations/{location_id}/devices")

async def get_internet_health(user_id: int, customer_id: str, location_id: str) -> dict:
    """Get internet connection health for a location."""
    return await plume_request(user_id, "GET", f"Customers/{customer_id}/locations/{location_id}/backhaul")

async def get_service_level(user_id: int, customer_id: str, location_id: str) -> dict:
    """Get service level status for a location."""
    return await plume_request(user_id, "GET", f"Customers/{customer_id}/locations/{location_id}/serviceLevel")

async def get_qoe_stats(user_id: int, customer_id: str, location_id: str) -> dict:
    """Get App QoE (Quality of Experience) metrics."""
    return await plume_request(user_id, "GET", f"Customers/{customer_id}/locations/{location_id}/appqoe/AppQoeStatsByTrafficClass")
    
async def get_wifi_networks(user_id: int, customer_id: str, location_id: str) -> list:
    """Get WiFi networks configured for a location."""
    return await plume_request(user_id, "GET", f"Customers/{customer_id}/locations/{location_id}/wifiNetworks")

# ============ SERVICE HEALTH ANALYSIS ============

def analyze_location_health(location: dict, service_level: dict, nodes: list, devices: list, qoe: dict) -> dict:
    """Comprehensive health analysis for a location."""
    health_report = {"online": False, "issues": [], "warnings": [], "disconnected_nodes": [], "summary": ""}
    
    health_report["online"] = service_level.get("connectionState", "").lower() == "connected"

    if isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict) and node.get("connectionState", "").lower() != "connected":
                nickname = node.get("nickname", node.get("id", "Unknown Pod"))
                health_report["disconnected_nodes"].append(nickname)
                health_report["issues"].append(f"🔴 Pod '{nickname}' is disconnected")

    if not health_report["online"]:
        health_report["summary"] = "🔴 LOCATION IS OFFLINE"
    elif health_report["issues"]:
        health_report["summary"] = "🟠 SERVICE DISRUPTED - Pods are disconnected"
    elif health_report["warnings"]:
        health_report["summary"] = "🟡 DEGRADED SERVICE"
    else:
        health_report["summary"] = "🟢 ALL SYSTEMS OPERATIONAL"

    return health_report
