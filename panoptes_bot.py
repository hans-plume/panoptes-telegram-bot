import os
from dotenv import load_dotenv

# Load environment variables from .env file before anything else
load_dotenv()

# Now, import and run the main bot logic from your renamed file
from bot_logic import main

if __name__ == "__main__":
    # Check if the token was loaded correctly
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        raise ValueError(
            "TELEGRAM_BOT_TOKEN not found. "
            "Ensure it's in your .env file or set as a system environment variable."
        )
    main()
