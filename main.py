# main.py
import logging
import sys
from datetime import datetime
import os
from src.trading_bot import EnhancedBitgetTradingBot

def setup_logging():
    """Konfiguruje system logowania"""
    # Stwórz folder logs jeśli nie istnieje
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Nazwa pliku z datą
    log_filename = f'logs/enhanced_bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # Konfiguracja logowania
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)  # Wyświetla też w konsoli
        ]
    )
    
    # Ustaw poziom dla ccxt na WARNING żeby zmniejszyć spam
    logging.getLogger('ccxt').setLevel(logging.WARNING)

def print_banner():
    """Wyświetla banner startowy"""
    banner = """
    ========================================
    🚀 Enhanced Bitget Futures Trading Bot 🚀
    ========================================
    
    Features:
    ✓ Scalping optimized (RSI 5-10)
    ✓ Order book analysis (L2 depth)
    ✓ Volume spike detection
    ✓ VWAP trading
    ✓ Session-based trading
    ✓ Advanced risk management
    
    Press Ctrl+C to stop
    Check logs/ folder for detailed logs
    """
    print(banner)

def main():
    """Główna funkcja aplikacji"""
    try:
        # Konfiguruj logowanie
        setup_logging()
        logger = logging.getLogger(__name__)
        
        # Wyświetl banner
        print_banner()
        
        # Sprawdź czy mamy API keys
        from config.settings import Config
        
        if not Config.BITGET_API_KEY or not Config.BITGET_API_SECRET:
            logger.error("API keys not found! Please check your .env file")
            sys.exit(1)
        
        # Sprawdź opcjonalne API keys
        if not Config.TWITTER_BEARER_TOKEN:
            logger.warning("Twitter API not configured - sentiment analysis will be limited")
        
        if not Config.CRYPTOPANIC_API_KEY:
            logger.warning("CryptoPanic API not configured - news sentiment will be limited")
        
        # Ostrzeżenie dla mainnet
        if not Config.USE_TESTNET:
            response = input("WARNING: Bot is configured for MAINNET. Are you sure? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Exiting...")
                sys.exit(0)
        
        # Informacja o trybie
        if Config.PAPER_TRADING:
            logger.info("Running in PAPER TRADING mode - all trades are simulated")
        else:
            logger.warning("Running in LIVE TRADING mode - real money will be used!")
        
        if Config.SCALPING_ENABLED:
            logger.info("Scalping mode is ENABLED")
            logger.info(f"Min profit: {Config.SCALPING_MIN_PROFIT_PERCENT}%")
            logger.info(f"Max hold time: {Config.SCALPING_MAX_HOLD_TIME} seconds")
        
        # Uruchom bota
        bot = EnhancedBitgetTradingBot()
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()