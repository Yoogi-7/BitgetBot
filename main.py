# main.py
import logging
import sys
from datetime import datetime
import os
from src.trading_bot import BitgetTradingBot

def setup_logging():
    """Konfiguruje system logowania"""
    # Stwórz folder logs jeśli nie istnieje
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Nazwa pliku z datą
    log_filename = f'logs/bitget_bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
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
    ================================
    🚀 Bitget Futures Trading Bot 🚀
    ================================
    
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
        
        # Ostrzeżenie dla mainnet
        if not Config.USE_TESTNET:
            response = input("WARNING: Bot is configured for MAINNET. Are you sure? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Exiting...")
                sys.exit(0)
        
        # Informacja o trybie paper trading
        if Config.PAPER_TRADING:
            logger.info("Running in PAPER TRADING mode - all trades are simulated")
        else:
            logger.warning("Running in LIVE TRADING mode - real money will be used!")
        
        # Uruchom bota
        bot = BitgetTradingBot()
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()