"""
Panoptes Telegram Bot - Plume Cloud Network Monitoring
========================================================

A production-ready Telegram bot for real-time monitoring of Plume Cloud networks.

Features:
- OAuth 2.0 authentication for secure API access
- Real-time health monitoring (nodes, devices, QoE)
- Multi-step guided OAuth setup
- Comprehensive service status reporting
- Automatic token refresh

Author: Hans V.
+ Nice Suit. John Philips, London. I Have Two Myself + H. Gruber +
License: MIT
"""

import logging
import os
from typing import Optional

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from plume_api_client import (
    set_user_auth,
    get_user_auth,
    is_oauth_token_valid,
    get_oauth_token,
    get_nodes_in_location,
    get_connected_devices,
    get_location_status,
    get_wifi_networks,
    get_service_level,
    get_qoe_stats,
    get_internet_health,
    analyze_location_health,
    PlumeAPIError,
    PLUME_SSO_URL,
    PLUME_API_BASE,
    user_auth,
)

# ============ CONFIGURATION & INITIALIZATION ============

# Configure logging for debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ CONVERSATION STATE MACHINE ============
# These constants define the OAuth authentication flow states
# Each state represents a step in the 4-step OAuth setup process
(
    ASK_AUTH_HEADER,       # State 1: Ask for Bearer token/authorization header
    ASK_PARTNER_ID,        # State 2: Ask for Plume Partner ID
    ASK_PLUME_API_BASE,    # State 3: Ask for Plume API base URL (optional)
    CONFIRM_AUTH,          # State 4: Confirm and test OAuth connection
) = range(4)


# ============ RESPONSE FORMATTERS ============
# These functions format raw API data into Telegram-friendly markdown messages
# Each formatter takes API response data and returns a formatted string

def format_nodes_response(nodes: list) -> str:
    """
    Format nodes/gateways list for Telegram display.
    
    Transforms API node data into a readable list with:
    - Node nickname/ID
    - Connection status
    - Model information
    - Firmware version
    
    Args:
        nodes: List of node dictionaries from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    if not nodes:
        return "No nodes found for this location."

    lines = ["📡 *Nodes/Gateways*:"]
    for node in nodes:
        if not isinstance(node, dict):
            continue
        nickname = node.get("nickname", node.get("id", "Unknown"))
        status = node.get("connectionState", node.get("status", "unknown"))
        firmware = node.get("firmwareVersion", "N/A")
        model = node.get("model", "N/A")
        
        lines.append(f"• {nickname}")
        lines.append(f"  Status: *{status}*")
        lines.append(f"  Model: {model}")
        lines.append(f"  Firmware: {firmware}")

    return "\n".join(lines)


def format_devices_response(devices: list) -> str:
    """
    Format connected devices list for Telegram display.
    
    Shows:
    - Device name
    - Device type (phone, laptop, etc.)
    - MAC address
    - Connection status
    - Limits to 10 devices for readability
    
    Args:
        devices: List of device dictionaries from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    if not devices:
        return "No devices connected to this location."

    lines = ["📱 *Connected Devices*:"]
    count = 0
    for device in devices[:10]:  # Limit to 10 for readability
        if not isinstance(device, dict):
            continue
        mac = device.get("mac", "N/A")
        device_type = device.get("type", "Unknown")
        nickname = device.get("nickname", "Unnamed")
        status = device.get("connected", device.get("status", "unknown"))
        
        lines.append(f"• {nickname} ({device_type})")
        lines.append(f"  MAC: `{mac}`")
        lines.append(f"  Status: {status}")
        count += 1

    if len(devices) > 10:
        lines.append(f"\n... and {len(devices) - 10} more devices")

    return "\n".join(lines)


def format_location_health(location: dict, internet: dict) -> str:
    """
    Format location health and internet status for Telegram.
    
    Displays:
    - Location name
    - Internet/backhaul connection status
    - Speed test metrics (if available)
    - Connected device count
    
    Args:
        location: Location data dictionary from API
        internet: Internet health data from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    lines = ["🏠 *Location Health*:"]
    
    location_name = location.get("name", "Unknown Location")
    lines.append(f"*{location_name}*")
    
    # Internet health/backhaul status
    backhaul_status = internet.get("status", "unknown")
    lines.append(f"\nInternet: *{backhaul_status}*")
    
    # Speed test data if available - shows average speeds
    speed_tests = location.get("lastThirtyDaysSpeedTestAverages", {})
    if speed_tests:
        down = speed_tests.get("downloadMbps", "N/A")
        up = speed_tests.get("uploadMbps", "N/A")
        lines.append(f"Download: {down} Mbps | Upload: {up} Mbps")
    
    # Connected devices count for at-a-glance view
    devices_count = location.get("connectedDevicesCount", 0)
    lines.append(f"Connected Devices: {devices_count}")
    
    return "\n".join(lines)
...
"""
Panoptes Telegram Bot - Plume Cloud Network Monitoring
========================================================

A production-ready Telegram bot for real-time monitoring of Plume Cloud networks.

Features:
- OAuth 2.0 authentication for secure API access
- Real-time health monitoring (nodes, devices, QoE)
- Multi-step guided OAuth setup
- Comprehensive service status reporting
- Automatic token refresh

Author: Hans V.
License: MIT
"""

import logging
import os
from typing import Optional

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from plume_api_client import (
    set_user_auth,
    get_user_auth,
    is_oauth_token_valid,
    get_oauth_token,
    get_nodes_in_location,
    get_connected_devices,
    get_location_status,
    get_wifi_networks,
    get_service_level,
    get_qoe_stats,
    get_internet_health,
    analyze_location_health,
    PlumeAPIError,
    PLUME_SSO_URL,
    PLUME_API_BASE,
    user_auth,
)

# ============ CONFIGURATION & INITIALIZATION ============

# Configure logging for debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ CONVERSATION STATE MACHINE ============
# These constants define the OAuth authentication flow states
# Each state represents a step in the 4-step OAuth setup process
(
    ASK_AUTH_HEADER,       # State 1: Ask for Bearer token/authorization header
    ASK_PARTNER_ID,        # State 2: Ask for Plume Partner ID
    ASK_PLUME_API_BASE,    # State 3: Ask for Plume API base URL (optional)
    CONFIRM_AUTH,          # State 4: Confirm and test OAuth connection
) = range(4)


# ============ RESPONSE FORMATTERS ============
# These functions format raw API data into Telegram-friendly markdown messages
# Each formatter takes API response data and returns a formatted string

def format_nodes_response(nodes: list) -> str:
    """
    Format nodes/gateways list for Telegram display.
    
    Transforms API node data into a readable list with:
    - Node nickname/ID
    - Connection status
    - Model information
    - Firmware version
    
    Args:
        nodes: List of node dictionaries from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    if not nodes:
        return "No nodes found for this location."

    lines = ["📡 *Nodes/Gateways*:"]
    for node in nodes:
        if not isinstance(node, dict):
            continue
        nickname = node.get("nickname", node.get("id", "Unknown"))
        status = node.get("connectionState", node.get("status", "unknown"))
        firmware = node.get("firmwareVersion", "N/A")
        model = node.get("model", "N/A")
        
        lines.append(f"• {nickname}")
        lines.append(f"  Status: *{status}*")
        lines.append(f"  Model: {model}")
        lines.append(f"  Firmware: {firmware}")

    return "\n".join(lines)


def format_devices_response(devices: list) -> str:
    """
    Format connected devices list for Telegram display.
    
    Shows:
    - Device name
    - Device type (phone, laptop, etc.)
    - MAC address
    - Connection status
    - Limits to 10 devices for readability
    
    Args:
        devices: List of device dictionaries from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    if not devices:
        return "No devices connected to this location."

    lines = ["📱 *Connected Devices*:"]
    count = 0
    for device in devices[:10]:  # Limit to 10 for readability
        if not isinstance(device, dict):
            continue
        mac = device.get("mac", "N/A")
        device_type = device.get("type", "Unknown")
        nickname = device.get("nickname", "Unnamed")
        status = device.get("connected", device.get("status", "unknown"))
        
        lines.append(f"• {nickname} ({device_type})")
        lines.append(f"  MAC: `{mac}`")
        lines.append(f"  Status: {status}")
        count += 1

    if len(devices) > 10:
        lines.append(f"\n... and {len(devices) - 10} more devices")

    return "\n".join(lines)


def format_location_health(location: dict, internet: dict) -> str:
    """
    Format location health and internet status for Telegram.
    
    Displays:
    - Location name
    - Internet/backhaul connection status
    - Speed test metrics (if available)
    - Connected device count
    
    Args:
        location: Location data dictionary from API
        internet: Internet health data from API
        
    Returns:
        Formatted markdown string for Telegram
    """
    lines = ["🏠 *Location Health*:"]
    
    location_name = location.get("name", "Unknown Location")
    lines.append(f"*{location_name}*")
    
    # Internet health/backhaul status
    backhaul_status = internet.get("status", "unknown")
    lines.append(f"\nInternet: *{backhaul_status}*")
    
    # Speed test data if available - shows average speeds
    speed_tests = location.get("lastThirtyDaysSpeedTestAverages", {})
    if speed_tests:
        down = speed_tests.get("downloadMbps", "N/A")
        up = speed_tests.get("uploadMbps", "N/A")
        lines.append(f"Download: {down} Mbps | Upload: {up} Mbps")
    
    # Connected devices count for at-a-glance view
    devices_count = location.get("connectedDevicesCount", 0)
    lines.append(f"Connected Devices: {devices_count}")
    
    return "\n".join(lines)
...
