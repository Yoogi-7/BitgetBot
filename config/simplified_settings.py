# config/simplified_settings.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Bitget API
    BITGET_API_KEY = os.getenv('BITGET_API_KEY', '')
    BITGET_API_SECRET = os.getenv('BITGET_API_SECRET', '')
    BITGET_PASSPHRASE = os.getenv('BITGET_PASSPHRASE', '')
    
    # Trading symbols - Only major pairs for testing
    TRADING_SYMBOLS = [
        'BTC/USDT:USDT',
        'ETH/USDT:USDT',
        'SOL/USDT:USDT',
    ]
    
    # Default symbol
    DEFAULT_SYMBOL = 'BTC/USDT:USDT'
    TRADING_SYMBOL = DEFAULT_SYMBOL
    
    # Timeframes
    TIMEFRAMES = ['1m']  # Start with single timeframe
    DEFAULT_TIMEFRAME = '1m'
    
    # Very relaxed filtering for testing
    MIN_VOLATILITY = 0.001          # 0.1% minimum volatility
    MIN_VOLUME_USD = 10000          # $10k minimum 24h volume
    MIN_VOLUME_RATIO = 0.1          # Very low threshold
    MIN_LIQUIDITY_USD = 1000        # $1k minimum in order book
    MIN_SPREAD_LIQUIDITY = 0.01     # 1% max spread
    
    # Signal strength thresholds
    MIN_SIGNAL_STRENGTH = 50        # Lower threshold for testing
    STRONG_SIGNAL_THRESHOLD = 70    
    WEAK_SIGNAL_THRESHOLD = 40      
    
    # Disable sentiment for simplicity
    SENTIMENT_ALIGNMENT_REQUIRED = False
    SENTIMENT_DISAGREEMENT_PENALTY = 0
    
    # Simplified trading parameters
    LEVERAGE = 5
    MARGIN_MODE = 'isolated'
    TRADE_AMOUNT_USDT = 50
    MAX_POSITION_SIZE = 200
    RISK_PER_TRADE = 0.01
    
    # Risk management
    STOP_LOSS_PERCENT = 2.0
    TAKE_PROFIT_PERCENT = 3.0
    MAX_DAILY_LOSS = 100
    MAX_OPEN_POSITIONS = 1  # Start with one position
    MAX_POSITIONS_PER_SYMBOL = 1
    MAX_TOTAL_POSITIONS = 1
    
    # Technical indicators (simplified)
    RSI_PERIODS = [5, 14]
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_EXTREME_OVERSOLD = 20
    RSI_EXTREME_OVERBOUGHT = 80
    
    # EMA periods
    EMA_SHORT = 9
    EMA_LONG = 21
    EMA_VERY_SHORT = 5
    EMA_TREND = 50
    
    # ATR
    ATR_PERIOD = 14
    ATR_PERIOD_SHORT = 5
    
    # Volume thresholds
    VOLUME_SPIKE_THRESHOLD = 2.0  # 200% spike
    VOLUME_SPIKE_EXTREME = 1.5    
    
    # Order book
    ORDER_BOOK_DEPTH = 10
    ORDER_BOOK_LEVELS = 5
    ORDER_BOOK_IMBALANCE_THRESHOLD = 0.2  # Less strict
    ORDER_BOOK_EXTREME_IMBALANCE = 0.5
    
    # Pattern detection
    PATTERNS_ENABLED = False  # Disable for now
    
    # Disable ML for simplicity
    USE_ML_MODELS = False
    
    # Scalping
    SCALPING_ENABLED = True
    SCALPING_MIN_PROFIT_PERCENT = 0.1
    SCALPING_MAX_HOLD_TIME = 300
    
    # System
    CHECK_INTERVAL = 30
    LOG_LEVEL = 'INFO'
    PAPER_TRADING = True
    
    # Disable notifications for testing
    TELEGRAM_BOT_TOKEN = ''
    TELEGRAM_CHAT_ID = ''
    
    # Risk management (simplified)
    SMALL_LOSS_THRESHOLD = 0.01
    BIG_LOSS_THRESHOLD = 0.02
    PENALTY_MULTIPLIER = 2
    EXCLUSION_PERIOD = 300  # 5 minutes
    
    # API URLs
    FEAR_GREED_API = "https://api.alternative.me/fng/"