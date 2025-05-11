# main.py
import os
import sys
import signal
import logging
from datetime import datetime
from src.bot import TradingBot
from config.settings import Config
from src.multi_symbol_bot import MultiSymbolTradingBot


def setup_logging():
    """Configure logging system."""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f'logs/bot_{timestamp}.log'
    
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('ccxt').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("\n\nShutting down bot...")
    sys.exit(0)


def main():
    """Main entry point."""
    # Określ tryb pracy
    MULTI_SYMBOL_MODE = True  # Zmień na False dla pojedynczego symbolu
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Print startup banner
    logger.info("=" * 50)
    logger.info("    Bitget Futures Trading Bot")
    logger.info("=" * 50)
    logger.info(f"Mode: {'PAPER TRADING' if Config.PAPER_TRADING else 'LIVE TRADING'}")
    
    if MULTI_SYMBOL_MODE:
        logger.info(f"Symbols: {', '.join(Config.TRADING_SYMBOLS)}")
    else:
        logger.info(f"Symbol: {Config.TRADING_SYMBOL}")
    
    logger.info(f"Leverage: {Config.LEVERAGE}x")
    
    # Check API keys
    if not all([Config.BITGET_API_KEY, Config.BITGET_API_SECRET, Config.BITGET_PASSPHRASE]):
        logger.error("Missing API credentials. Please check your .env file.")
        sys.exit(1)
    
    # Confirm live trading if enabled
    if not Config.PAPER_TRADING:
        response = input("WARNING: Live trading enabled. Continue? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Exiting...")
            sys.exit(0)
    
    try:
        # Initialize and run bot
        if MULTI_SYMBOL_MODE:
            bot = MultiSymbolTradingBot()
        else:
            bot = TradingBot()
        
        bot.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()