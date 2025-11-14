import logging
import os
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError

from plume_api_client import (
    get_oauth_token,
    is_oauth_token_valid,
    set_user_auth,
    get_nodes_in_location,
    get_connected_devices,
    get_service_level,
    get_qoe_stats,
    analyze_location_health,
    PlumeAPIError,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('panoptes_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError('TELEGRAM_BOT_TOKEN environment variable is not set')

STATE_SSO_URL, STATE_AUTH_HEADER, STATE_PARTNER_ID, STATE_API_BASE = range(4)

user_context = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command and show main menu."""
    user_id = update.effective_user.id
    
    welcome_text = (
        "🔐 Welcome to Panoptes Bot!\n\n"
        "This bot helps you monitor your Plume Cloud network in real-time.\n\n"
        "Commands:\n"
        "/auth - Set up OAuth authentication\n"
        "/health - Check network health\n"
        "/nodes - View connected nodes\n"
        "/devices - View connected devices\n"
        "/status - Full network status\n"
        "/help - Show this message"
    )
    
    if user_id not in user_context or not is_oauth_token_valid(user_id):
        welcome_text += "\n\n⚠️ Please run /auth first to authenticate."
    
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = (
        "📚 **Available Commands:**\n\n"
        "🔐 *Authentication*\n"
        "/auth - Set up OAuth 2.0 authentication\n\n"
        "📊 *Network Monitoring*\n"
        "/health - Check overall network health\n"
        "/nodes - List all connected nodes\n"
        "/devices - List connected devices\n"
        "/wifi - WiFi pod status\n"
        "/status - Full network report\n\n"
        "💡 *Tips*\n"
        "- Run /auth first to authenticate\n"
        "- Use /health for quick status check\n"
        "- Use /status for detailed report"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def start_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start OAuth conversation."""
    await update.message.reply_text(
        "🔐 OAuth 2.0 Setup\n\n"
        "Step 1/4: Enter your SSO URL\n"
        "Example: https://external.sso.plume.com/oauth2/{auth-id}/v1/token"
    )
    return STATE_SSO_URL

async def receive_sso_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate SSO URL."""
    user_id = update.effective_user.id
    sso_url = update.message.text.strip()
    
    if not sso_url.startswith('https://') or 'oauth2' not in sso_url:
        await update.message.reply_text(
            "❌ Invalid SSO URL. Must start with https:// and contain 'oauth2'."
        )
        return STATE_SSO_URL
    
    user_context[user_id] = {'sso_url': sso_url}
    await update.message.reply_text(
        "✅ SSO URL saved.\n\n"
        "Step 2/4: Enter your authorization header\n"
        "Example: Authorization: Bearer YOUR_TOKEN"
    )
    return STATE_AUTH_HEADER

async def receive_auth_header(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate auth header."""
    user_id = update.effective_user.id
    auth_header = update.message.text.strip()
    
    if not auth_header or 'Bearer' not in auth_header and 'bearer' not in auth_header:
        await update.message.reply_text(
            "❌ Invalid format. Use: Bearer YOUR_TOKEN"
        )
        return STATE_AUTH_HEADER
    
    user_context[user_id]['auth_header'] = auth_header
    await update.message.reply_text(
        "✅ Auth header saved.\n\n"
        "Step 3/4: Enter your Partner ID\n"
        "Example: 12345"
    )
    return STATE_PARTNER_ID

async def receive_partner_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate Partner ID."""
    user_id = update.effective_user.id
    partner_id = update.message.text.strip()
    
    if not partner_id.isdigit():
        await update.message.reply_text(
            "❌ Partner ID must be numeric."
        )
        return STATE_PARTNER_ID
    
    user_context[user_id]['partner_id'] = partner_id
    await update.message.reply_text(
        "✅ Partner ID saved.\n\n"
        "Step 4/4: Enter your API Base URL\n"
        "Example: https://api.plume.com/cloud/v1"
    )
    return STATE_API_BASE

async def receive_api_base(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive API base URL and complete setup."""
    user_id = update.effective_user.id
    api_base = update.message.text.strip()
    
    if not api_base.startswith('https://'):
        await update.message.reply_text(
            "❌ API base must start with https://"
        )
        return STATE_API_BASE
    
    try:
        user_context[user_id]['api_base'] = api_base
        
        set_user_auth(
            user_id,
            user_context[user_id]['sso_url'],
            user_context[user_id]['auth_header'],
            user_context[user_id]['partner_id'],
            api_base
        )
        
        token = get_oauth_token(user_id)
        if token:
            await update.message.reply_text(
                "✅ **OAuth Setup Complete!**\n\n"
                "Your Plume Cloud authentication is ready.\n"
                "Use /health to check your network status.",
                parse_mode='Markdown'
            )
            logger.info(f"OAuth setup completed for user {user_id}")
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ Failed to obtain OAuth token. Please check your credentials and try /auth again."
            )
            return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"OAuth setup error for user {user_id}: {str(e)}")
        await update.message.reply_text(
            f"❌ Setup failed: {str(e)}\n\nPlease try /auth again."
        )
        return ConversationHandler.END

async def cancel_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel OAuth setup."""
    await update.message.reply_text("❌ OAuth setup cancelled.")
    return ConversationHandler.END

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check network health."""
    user_id = update.effective_user.id
    
    if not is_oauth_token_valid(user_id):
        await update.message.reply_text(
            "❌ Authentication required. Please run /auth first."
        )
        return
    
    try:
        async with update.message.chat.send_action('typing'):
            health = await analyze_location_health(user_id)
            report = format_health_report(health)
            await update.message.reply_text(report, parse_mode='Markdown')
    
    except PlumeAPIError as e:
        if e.status_code in [401, 403]:
            await update.message.reply_text(
                "❌ Authentication failed. Please run /auth again."
            )
        else:
            await update.message.reply_text(f"❌ API Error: {str(e)}")
        logger.error(f"API error for user {user_id}: {str(e)}")
    except Exception as e:
        await update.message.reply_text("❌ An error occurred. Please try again.")
        logger.error(f"Error in health_command for user {user_id}: {str(e)}")

async def nodes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List connected nodes."""
    user_id = update.effective_user.id
    
    if not is_oauth_token_valid(user_id):
        await update.message.reply_text(
            "❌ Authentication required. Please run /auth first."
        )
        return
    
    try:
        async with update.message.chat.send_action('typing'):
            nodes = await get_nodes_in_location(user_id)
            report = format_nodes_response(nodes)
            await update.message.reply_text(report, parse_mode='Markdown')
    
    except PlumeAPIError as e:
        if e.status_code in [401, 403]:
            await update.message.reply_text(
                "❌ Authentication failed. Please run /auth again."
            )
        else:
            await update.message.reply_text(f"❌ API Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text("❌ An error occurred. Please try again.")
        logger.error(f"Error in nodes_command for user {user_id}: {str(e)}")

async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List connected devices."""
    user_id = update.effective_user.id
    
    if not is_oauth_token_valid(user_id):
        await update.message.reply_text(
            "❌ Authentication required. Please run /auth first."
        )
        return
    
    try:
        async with update.message.chat.send_action('typing'):
            devices = await get_connected_devices(user_id)
            report = format_devices_response(devices)
            await update.message.reply_text(report, parse_mode='Markdown')
    
    except PlumeAPIError as e:
        if e.status_code in [401, 403]:
            await update.message.reply_text(
                "❌ Authentication failed. Please run /auth again."
            )
        else:
            await update.message.reply_text(f"❌ API Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text("❌ An error occurred. Please try again.")
        logger.error(f"Error in devices_command for user {user_id}: {str(e)}")

async def wifi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show WiFi pod status."""
    user_id = update.effective_user.id
    
    if not is_oauth_token_valid(user_id):
        await update.message.reply_text(
            "❌ Authentication required. Please run /auth first."
        )
        return
    
    try:
        async with update.message.chat.send_action('typing'):
            nodes = await get_nodes_in_location(user_id)
            report = format_wifi_status(nodes)
            await update.message.reply_text(report, parse_mode='Markdown')
    
    except PlumeAPIError as e:
        if e.status_code in [401, 403]:
            await update.message.reply_text(
                "❌ Authentication failed. Please run /auth again."
            )
        else:
            await update.message.reply_text(f"❌ API Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text("❌ An error occurred. Please try again.")
        logger.error(f"Error in wifi_command for user {user_id}: {str(e)}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full network status."""
    user_id = update.effective_user.id
    
    if not is_oauth_token_valid(user_id):
        await update.message.reply_text(
            "❌ Authentication required. Please run /auth first."
        )
        return
    
    try:
        async with update.message.chat.send_action('typing'):
            health = await analyze_location_health(user_id)
            nodes = await get_nodes_in_location(user_id)
            devices = await get_connected_devices(user_id)
            
            status_report = (
                "📊 **Full Network Status**\n\n"
                + format_health_report(health) + "\n"
                + format_nodes_response(nodes) + "\n"
                + format_devices_response(devices)
            )
            
            await update.message.reply_text(status_report, parse_mode='Markdown')
    
    except PlumeAPIError as e:
        if e.status_code in [401, 403]:
            await update.message.reply_text(
                "❌ Authentication failed. Please run /auth again."
            )
        else:
            await update.message.reply_text(f"❌ API Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text("❌ An error occurred. Please try again.")
        logger.error(f"Error in status_command for user {user_id}: {str(e)}")

def format_health_report(health):
    """Format health analysis as readable report."""
    status_icon = health['status_icon']
    status_text = health['status_text']
    
    report = f"{status_icon} **Network Health: {status_text}**\n\n"
    report += f"🟢 Online nodes: {health['online_nodes']}/{health['total_nodes']}\n"
    report += f"🔗 Connected pods: {health['connected_pods']}/{health['total_pods']}\n"
    report += f"📱 Connected devices: {health['connected_devices']}/{health['total_devices']}\n"
    report += f"⚡ QoE score: {health['qoe_score']}/100\n"
    
    return report

def format_nodes_response(nodes):
    """Format nodes data as readable list."""
    report = "🖥️  **Connected Nodes**\n\n"
    
    if not nodes:
        report += "No nodes found."
        return report
    
    for node in nodes[:10]:
        status = "🟢" if node.get('online') else "🔴"
        name = node.get('name', 'Unknown')
        ip = node.get('ip', 'N/A')
        report += f"{status} {name} ({ip})\n"
    
    if len(nodes) > 10:
        report += f"\n... and {len(nodes) - 10} more nodes"
    
    return report

def format_devices_response(devices):
    """Format devices data as readable list."""
    report = "📱 **Connected Devices**\n\n"
    
    if not devices:
        report += "No devices found."
        return report
    
    for device in devices[:10]:
        device_type = device.get('type', 'Unknown')
        name = device.get('name', 'Unknown')
        signal = device.get('signal_strength', 0)
        report += f"📶 {name} ({device_type}) - Signal: {signal}%\n"
    
    if len(devices) > 10:
        report += f"\n... and {len(devices) - 10} more devices"
    
    return report

def format_wifi_status(nodes):
    """Format WiFi pod status."""
    report = "📡 **WiFi Pod Status**\n\n"
    
    wifi_pods = [n for n in nodes if n.get('type') == 'pod']
    
    if not wifi_pods:
        report += "No WiFi pods found."
        return report
    
    for pod in wifi_pods[:10]:
        status = "🟢" if pod.get('online') else "🔴"
        name = pod.get('name', 'Unknown')
        signal_strength = pod.get('signal_strength', 0)
        report += f"{status} {name} - Signal: {signal_strength}%\n"
    
    if len(wifi_pods) > 10:
        report += f"\n... and {len(wifi_pods) - 10} more pods"
    
    return report

def main():
    """Start the bot."""
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('auth', start_auth)],
        states={
            STATE_SSO_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sso_url)],
            STATE_AUTH_HEADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_auth_header)],
            STATE_PARTNER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_partner_id)],
            STATE_API_BASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_base)],
        },
        fallbacks=[CommandHandler('cancel', cancel_auth)],
    )
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('health', health_command))
    app.add_handler(CommandHandler('nodes', nodes_command))
    app.add_handler(CommandHandler('devices', devices_command))
    app.add_handler(CommandHandler('wifi', wifi_command))
    app.add_handler(CommandHandler('status', status_command))
    app.add_handler(conv_handler)
    
    logger.info("Starting Panoptes Telegram Bot")
    app.run_polling()

if __name__ == '__main__':
    main()
