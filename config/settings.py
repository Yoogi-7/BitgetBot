# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Bitget API
    BITGET_API_KEY = os.getenv('BITGET_API_KEY', '')
    BITGET_API_SECRET = os.getenv('BITGET_API_SECRET', '')
    BITGET_PASSPHRASE = os.getenv('BITGET_PASSPHRASE', '')
    
    # Trading symbols - Multi-symbol support (updated list)
    TRADING_SYMBOLS = [
        'BTC/USDT:USDT',
        'ETH/USDT:USDT',
        'SOL/USDT:USDT',
        'AVAX/USDT:USDT',
        'XRP/USDT:USDT',
        'POL/USDT:USDT',    # Changed from MATIC
        'DOGE/USDT:USDT',
        'DOT/USDT:USDT',
        'LINK/USDT:USDT',
        'UNI/USDT:USDT'
    ]
    
    # Default symbol for backward compatibility
    DEFAULT_SYMBOL = 'BTC/USDT:USDT'
    TRADING_SYMBOL = DEFAULT_SYMBOL  # Alias
    
    # Timeframes
    TIMEFRAMES = ['1m', '3m', '5m']
    DEFAULT_TIMEFRAME = '1m'
    
    # Dynamic filtering thresholds (relaxed for testing)
    MIN_VOLATILITY = 0.002          # 0.2% minimum volatility (was 0.5%)
    MIN_VOLUME_USD = 100000         # $100k minimum 24h volume (was $1M)
    MIN_VOLUME_RATIO = 0.3          # Current volume vs average (was 0.5)
    MIN_LIQUIDITY_USD = 10000       # $10k minimum in order book (was $50k)
    MIN_SPREAD_LIQUIDITY = 0.005    # 0.5% max spread for liquidity (was 0.2%)
    
    # Signal strength thresholds
    MIN_SIGNAL_STRENGTH = 65        # Minimum signal strength (0-100)
    STRONG_SIGNAL_THRESHOLD = 80    # Strong signal threshold
    WEAK_SIGNAL_THRESHOLD = 50      # Weak signal threshold
    
    # Sentiment alignment
    SENTIMENT_ALIGNMENT_REQUIRED = False  # Disabled for initial testing
    SENTIMENT_DISAGREEMENT_PENALTY = 20  # Penalty for sentiment mismatch
    
    # Correlation settings
    CORRELATION_WINDOW = 24         # Hours for correlation calculation
    HIGH_CORRELATION_THRESHOLD = 0.7
    
    # Multi-symbol management
    MAX_POSITIONS_PER_SYMBOL = 1
    MAX_TOTAL_POSITIONS = 5
    SYMBOL_ALLOCATION_MODE = 'equal'  # 'equal', 'volatility_weighted', 'strength_weighted'
    
    # Trading parameters
    LEVERAGE = 5
    MARGIN_MODE = 'isolated'
    
    # Position sizing
    TRADE_AMOUNT_USDT = 50
    MAX_POSITION_SIZE = 200
    RISK_PER_TRADE = 0.01  # 1% kapitału na transakcję
    
    # Risk management
    STOP_LOSS_PERCENT = 2.0
    TAKE_PROFIT_PERCENT = 3.0
    MAX_DAILY_LOSS = 100
    MAX_OPEN_POSITIONS = 3
    
    # Penalty thresholds
    SMALL_LOSS_THRESHOLD = 0.005  # 0.5% straty = kara ×3
    BIG_LOSS_THRESHOLD = 0.01     # 1% straty = wykluczenie sygnałów
    PENALTY_MULTIPLIER = 3        # Mnożnik kary
    EXCLUSION_PERIOD = 3600       # Czas wykluczenia w sekundach (1 godzina)
    
    # Technical indicators
    RSI_PERIODS = [5, 6, 7, 8, 9, 10, 14]
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_EXTREME_OVERSOLD = 20
    RSI_EXTREME_OVERBOUGHT = 80
    
    # EMA periods
    EMA_SHORT = 9
    EMA_LONG = 21
    EMA_FAST = 9  # Alias
    EMA_SLOW = 21  # Alias
    EMA_VERY_SHORT = 5
    EMA_TREND = 50
    
    # SMA periods
    SMA_PERIODS = [10, 20, 50]
    
    # MACD parameters
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Bollinger Bands
    BB_PERIOD = 20
    BB_STD = 2
    BB_SQUEEZE_THRESHOLD = 0.02
    
    # ATR
    ATR_PERIOD = 14
    ATR_PERIOD_SHORT = 5
    
    # Volume thresholds (relaxed)
    VOLUME_SPIKE_THRESHOLD = 3.0  # 300% wzrost (was 500%)
    VOLUME_SPIKE_EXTREME = 2.0    # 200% powyżej średniej (was 300%)
    
    # Order book parameters
    ORDER_BOOK_DEPTH = 20
    ORDER_BOOK_LEVELS = 5
    LIQUIDITY_MIN_THRESHOLD = 10000
    ORDER_BOOK_IMBALANCE_THRESHOLD = 0.3
    ORDER_BOOK_EXTREME_IMBALANCE = 0.6
    SPREAD_MULTIPLIER = 2
    
    # Market data
    FUNDING_RATE_THRESHOLD = 0.05
    OPEN_INTEREST_CHANGE_THRESHOLD = 0.1
    
    # Pattern detection
    PATTERNS_ENABLED = True
    PATTERN_CONFIDENCE_THRESHOLD = 0.7
    
    # Sentiment analysis
    SENTIMENT_UPDATE_INTERVAL = 300
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN', '')
    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', '')
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', '')
    CRYPTOPANIC_API_KEY = os.getenv('CRYPTOPANIC_API_KEY', '')
    NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')
    
    # Sentiment sources
    SENTIMENT_SOURCES = ['twitter', 'reddit', 'fear_greed', 'news']
    SENTIMENT_WEIGHT = {
        'twitter': 0.3,
        'reddit': 0.2,
        'fear_greed': 0.3,
        'news': 0.2
    }
    
    # Machine Learning
    USE_ML_MODELS = False
    LSTM_LOOKBACK = 60
    ENSEMBLE_MODELS = 3
    
    # Session timing (UTC)
    ASIAN_SESSION = (0, 8)
    EUROPEAN_SESSION = (7, 16)
    US_SESSION = (13, 22)
    HIGH_LIQUIDITY_HOURS = (13, 16)
    
    # Scalping parameters
    SCALPING_ENABLED = True
    SCALPING_MIN_PROFIT_PERCENT = 0.1
    SCALPING_MAX_HOLD_TIME = 300
    
    # System settings
    CHECK_INTERVAL = 30
    LOG_LEVEL = 'INFO'
    PAPER_TRADING = True
    
    # Notifications
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # API URLs
    FEAR_GREED_API = "https://api.alternative.me/fng/"
    REDDIT_API = "https://oauth.reddit.com"
    NEWS_API = "https://newsapi.org/v2/everything"