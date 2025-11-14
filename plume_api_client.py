import httpx
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class PlumeAPIError(Exception):
    """Exception for Plume API errors."""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

user_auth_store = {}

def set_user_auth(
    user_id: int,
    sso_url: str,
    auth_header: str,
    partner_id: str,
    api_base: str
):
    """Store user authentication details."""
    user_auth_store[user_id] = {
        'sso_url': sso_url,
        'auth_header': auth_header,
        'partner_id': partner_id,
        'api_base': api_base,
        'oauth_token': None,
        'token_expiry': None,
    }
    logger.info(f"Auth stored for user {user_id}")

async def get_oauth_token(user_id: int) -> Optional[str]:
    """Get valid OAuth token for user, refreshing if needed."""
    if user_id not in user_auth_store:
        logger.warning(f"No auth found for user {user_id}")
        return None
    
    user_auth = user_auth_store[user_id]
    
    if (
        user_auth.get('oauth_token') and
        user_auth.get('token_expiry') and
        datetime.now() < (user_auth['token_expiry'] - timedelta(seconds=60))
    ):
        logger.debug(f"Using cached token for user {user_id}")
        return user_auth['oauth_token']
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                user_auth['sso_url'],
                headers={
                    'Authorization': user_auth['auth_header'],
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                data={
                    'grant_type': 'client_credentials',
                    'scope': f'partnerId:{user_auth["partner_id"]} role:partnerIdAdmin',
                }
            )
            
            if response.status_code != 200:
                raise PlumeAPIError(
                    f"OAuth token request failed: {response.text}",
                    status_code=response.status_code
                )
            
            data = response.json()
            token = data.get('access_token')
            expires_in = data.get('expires_in', 3600)
            
            user_auth['oauth_token'] = token
            user_auth['token_expiry'] = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info(f"OAuth token refreshed for user {user_id}")
            return token
    
    except httpx.RequestError as e:
        logger.error(f"HTTP error during OAuth: {str(e)}")
        raise PlumeAPIError(f"Failed to get OAuth token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during OAuth: {str(e)}")
        raise PlumeAPIError(f"Unexpected error during OAuth: {str(e)}")

def is_oauth_token_valid(user_id: int) -> bool:
    """Check if user has valid authentication."""
    if user_id not in user_auth_store:
        return False
    
    user_auth = user_auth_store[user_id]
    
    if not user_auth.get('oauth_token'):
        return False
    
    if user_auth.get('token_expiry'):
        if datetime.now() >= user_auth['token_expiry']:
            return False
    
    return True

async def _make_api_request(
    user_id: int,
    method: str,
    endpoint: str,
    **kwargs
) -> Dict[str, Any]:
    """Make authenticated API request to Plume."""
    if user_id not in user_auth_store:
        raise PlumeAPIError("User not authenticated")
    
    token = await get_oauth_token(user_id)
    if not token:
        raise PlumeAPIError("Failed to obtain OAuth token")
    
    user_auth = user_auth_store[user_id]
    url = f"{user_auth['api_base']}{endpoint}"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if method.upper() == 'GET':
                response = await client.get(url, headers=headers, **kwargs)
            elif method.upper() == 'POST':
                response = await client.post(url, headers=headers, **kwargs)
            else:
                raise PlumeAPIError(f"Unsupported HTTP method: {method}")
            
            if response.status_code in [401, 403]:
                user_auth_store[user_id]['oauth_token'] = None
                raise PlumeAPIError(
                    "Authentication failed",
                    status_code=response.status_code
                )
            
            if response.status_code >= 400:
                raise PlumeAPIError(
                    f"API error: {response.text}",
                    status_code=response.status_code
                )
            
            return response.json()
    
    except httpx.RequestError as e:
        logger.error(f"HTTP error in API request: {str(e)}")
        raise PlumeAPIError(f"API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in API request: {str(e)}")
        raise PlumeAPIError(f"Unexpected error in API request: {str(e)}")

async def get_nodes_in_location(user_id: int) -> List[Dict[str, Any]]:
    """Get all nodes in user's location."""
    try:
        data = await _make_api_request(user_id, 'GET', '/location/nodes')
        return data.get('data', [])
    except PlumeAPIError:
        raise
    except Exception as e:
        logger.error(f"Error fetching nodes: {str(e)}")
        raise PlumeAPIError(f"Failed to fetch nodes: {str(e)}")

async def get_connected_devices(user_id: int) -> List[Dict[str, Any]]:
    """Get connected devices from Plume Cloud."""
    try:
        data = await _make_api_request(user_id, 'GET', '/devices')
        return data.get('data', [])
    except PlumeAPIError:
        raise
    except Exception as e:
        logger.error(f"Error fetching devices: {str(e)}")
        raise PlumeAPIError(f"Failed to fetch devices: {str(e)}")

async def get_service_level(user_id: int) -> Dict[str, Any]:
    """Get service level/health from Plume Cloud."""
    try:
        data = await _make_api_request(user_id, 'GET', '/service-health')
        return data.get('data', {})
    except PlumeAPIError:
        raise
    except Exception as e:
        logger.error(f"Error fetching service level: {str(e)}")
        raise PlumeAPIError(f"Failed to fetch service level: {str(e)}")

async def get_qoe_stats(user_id: int) -> Dict[str, Any]:
    """Get QoE (Quality of Experience) statistics."""
    try:
        data = await _make_api_request(user_id, 'GET', '/qoe/stats')
        return data.get('data', {})
    except PlumeAPIError:
        raise
    except Exception as e:
        logger.error(f"Error fetching QoE stats: {str(e)}")
        raise PlumeAPIError(f"Failed to fetch QoE stats: {str(e)}")

async def get_wifi_connectivity(user_id: int) -> Dict[str, Any]:
    """Get WiFi pod connectivity status."""
    try:
        data = await _make_api_request(user_id, 'GET', '/pods/connectivity')
        return data.get('data', {})
    except PlumeAPIError:
        raise
    except Exception as e:
        logger.error(f"Error fetching WiFi connectivity: {str(e)}")
        raise PlumeAPIError(f"Failed to fetch WiFi connectivity: {str(e)}")

async def analyze_location_health(user_id: int) -> Dict[str, Any]:
    """Analyze overall location health and return status."""
    try:
        nodes = await get_nodes_in_location(user_id)
        devices = await get_connected_devices(user_id)
        service = await get_service_level(user_id)
        qoe = await get_qoe_stats(user_id)
        
        online_nodes = sum(1 for n in nodes if n.get('online', False))
        total_nodes = len(nodes)
        
        online_pods = sum(1 for n in nodes if n.get('online', False) and n.get('type') == 'pod')
        total_pods = sum(1 for n in nodes if n.get('type') == 'pod')
        
        connected_devices = len([d for d in devices if d.get('connected', False)])
        total_devices = len(devices)
        
        qoe_score = min(100, max(0, qoe.get('average_score', 50)))
        
        if online_nodes == total_nodes and qoe_score >= 80:
            status_icon = "🟢"
            status_text = "Excellent"
        elif online_nodes >= (total_nodes * 0.75) and qoe_score >= 60:
            status_icon = "🟡"
            status_text = "Good"
        elif online_nodes >= (total_nodes * 0.5) and qoe_score >= 40:
            status_icon = "🟠"
            status_text = "Fair"
        else:
            status_icon = "🔴"
            status_text = "Poor"
        
        return {
            'status_icon': status_icon,
            'status_text': status_text,
            'online_nodes': online_nodes,
            'total_nodes': total_nodes,
            'connected_pods': online_pods,
            'total_pods': total_pods,
            'connected_devices': connected_devices,
            'total_devices': total_devices,
            'qoe_score': qoe_score,
        }
    
    except PlumeAPIError:
        raise
    except Exception as e:
        logger.error(f"Error analyzing location health: {str(e)}")
        raise PlumeAPIError(f"Failed to analyze health: {str(e)}")
