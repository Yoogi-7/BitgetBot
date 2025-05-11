# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Bitget API
    BITGET_API_KEY = os.getenv('BITGET_API_KEY', '')
    BITGET_API_SECRET = os.getenv('BITGET_API_SECRET', '')
    BITGET_PASSPHRASE = os.getenv('BITGET_PASSPHRASE', '')
    
    # Trading parameters
    TRADING_SYMBOL = 'BTC/USDT:USDT'
    TIMEFRAME = '1m'
    LEVERAGE = 5
    MARGIN_MODE = 'isolated'
    
    # Position sizing
    TRADE_AMOUNT_USDT = 50
    MAX_POSITION_SIZE = 200
    
    # Risk management
    STOP_LOSS_PERCENT = 2.0
    TAKE_PROFIT_PERCENT = 3.0
    MAX_DAILY_LOSS = 100
    MAX_OPEN_POSITIONS = 3
    
    # Technical indicators
    RSI_PERIOD = 14
    RSI_OVERSOLD = 25
    RSI_OVERBOUGHT = 75
    EMA_FAST = 9
    EMA_SLOW = 21
    
    # Volume thresholds
    VOLUME_SPIKE_THRESHOLD = 5.0  # 500% increase
    
    # Order book parameters
    ORDER_BOOK_DEPTH = 20
    LIQUIDITY_MIN_THRESHOLD = 10000
    ORDER_BOOK_IMBALANCE_THRESHOLD = 0.3
    
    # Scalping parameters (if enabled)
    SCALPING_ENABLED = True
    SCALPING_MIN_PROFIT_PERCENT = 0.1
    SCALPING_MAX_HOLD_TIME = 300  # 5 minutes
    
    # System settings
    CHECK_INTERVAL = 30  # seconds
    LOG_LEVEL = 'INFO'
    PAPER_TRADING = True
    
    # Notifications
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')