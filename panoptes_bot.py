import os
import logging
fromimport os
import logging
from dotenv import load_dotenv
from bot_logic import main as bot_main  # Import the main function from bot_logic

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Load the environment variables and run the bot.
    """
    # Load environment variables from a .env file if it exists
    load_dotenv()

    # Get the Telegram bot token from the environment variable
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return

    # Run the bot's main logic, passing the token
    bot_main(token)

if __name__ == '__main__':
    main()
