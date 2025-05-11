# main_enhanced.py
import os
import sys
import signal
import logging
from datetime import datetime
from src.integrated_trading_bot import IntegratedTradingBot
from config.settings import Config


def setup_logging():
    """Configure logging system."""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f'logs/bot_enhanced_{timestamp}.log'
    
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


def display_risk_settings():
    """Display current risk management settings."""
    print("\n" + "="*50)
    print("     RISK MANAGEMENT SETTINGS")
    print("="*50)
    print(f"Dynamic Leverage: {Config.MIN_LEVERAGE}x - {Config.MAX_LEVERAGE}x")
    print(f"Max Risk Per Trade: {Config.MAX_RISK_PER_TRADE*100}%")
    print(f"Max Daily Loss: {Config.MAX_DAILY_LOSS_PERCENT}%")
    print(f"Max Positions: {Config.MAX_TOTAL_POSITIONS}")
    print(f"Max Consecutive Losses: {Config.MAX_CONSECUTIVE_LOSSES}")
    print(f"System Pause Duration: {Config.SYSTEM_PAUSE_MINUTES} minutes")
    print("="*50)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("\n\nShutting down bot gracefully...")
    sys.exit(0)


def main():
    """Main entry point."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Print startup banner
    logger.info("="*50)
    logger.info("    Enhanced Trading Bot with Risk Management")
    logger.info("="*50)
    logger.info(f"Mode: {'PAPER TRADING' if Config.PAPER_TRADING else 'LIVE TRADING'}")
    logger.info(f"Symbols: {', '.join(Config.TRADING_SYMBOLS[:3])}...")
    
    # Display risk settings
    display_risk_settings()
    
    # Check API keys
    if not all([Config.BITGET_API_KEY, Config.BITGET_API_SECRET, Config.BITGET_PASSPHRASE]):
        logger.error("Missing API credentials. Please check your .env file.")
        sys.exit(1)
    
    # Confirm live trading if enabled
    if not Config.PAPER_TRADING:
        print("\n" + "!"*50)
        print("WARNING: LIVE TRADING ENABLED")
        print("This bot will execute real trades with the following risk parameters:")
        print(f"- Dynamic leverage up to {Config.MAX_LEVERAGE}x")
        print(f"- Maximum {Config.MAX_RISK_PER_TRADE*100}% risk per trade")
        print(f"- Daily loss limit of {Config.MAX_DAILY_LOSS_PERCENT}%")
        print("!"*50)
        
        response = input("\nAre you absolutely sure you want to continue? (type 'YES' to confirm): ")
        if response != 'YES':
            logger.info("Live trading cancelled by user")
            sys.exit(0)
    
    try:
        # Initialize and run bot
        bot = IntegratedTradingBot()
        bot.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()