#!/usr/bin/env python3
"""
XAUUSD Scalping Signal Bot
Bot Telegram untuk sinyal trading XAUUSD dengan strategi scalping
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.config import Config
from src.telegram_bot import XAUUSDBot

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotRunner:
    """Main bot runner with graceful shutdown"""
    
    def __init__(self):
        self.bot: Optional[XAUUSDBot] = None
        self.shutdown_event = None # Will be initialized in start()
        
    async def start(self):
        """Start the bot"""
        try:
            # Initialize configuration
            Config.init_directories()
            
            # Initialize shutdown event
            self.shutdown_event = asyncio.Event()
            
            # Create bot instance
            self.bot = XAUUSDBot()
            
            # Start the bot
            await self.bot.start()
            
            logger.info("Bot started successfully!")
            logger.info("Press Ctrl+C to stop the bot")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
            
    async def stop(self):
        """Stop the bot gracefully"""
        logger.info("Shutting down bot...")
        
        if self.bot:
            await self.bot.stop()
            
        if self.shutdown_event:
            self.shutdown_event.set()
        logger.info("Bot stopped successfully")
        
    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        if self.shutdown_event:
            asyncio.create_task(self.stop())
        
async def main():
    """Main entry point"""
    runner = BotRunner()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, runner.handle_signal)   # Ctrl+C
    signal.signal(signal.SIGTERM, runner.handle_signal)  # Termination
    
    try:
        await runner.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    # Check if bot token is configured
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token or token == 'YOUR_TELEGRAM_BOT_TOKEN_HERE':
        print("❌ ERROR: Telegram Bot Token belum dikonfigurasi!")
        print("\nSilakan lakukan langkah berikut:")
        print("1. Buat bot di @BotFather di Telegram")
        print("2. Salin token bot Anda")
        print("3. Gunakan tab Secrets di Replit untuk menyimpan TELEGRAM_BOT_TOKEN")
        print("4. Jalankan bot lagi")
        sys.exit(1)
        
    # Run the bot
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot dihentikan oleh user")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nError: {e}")
        sys.exit(1)