#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set environment variables for the bot
os.environ['TELEGRAM_BOT_TOKEN'] = '8382732712:AAH1cbbeOSOqIfneT7cvG2T6zsoBwrNQvAg'

# Import and run the bot
from telegram_bot import main

if __name__ == '__main__':
    print("Starting Telegram bot...")
    main()

