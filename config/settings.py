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
    TIMEFRAMES = ['1m', '3m', '5m']  # Multiple timeframes for analysis
    DEFAULT_TIMEFRAME = '1m'
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
    RSI_PERIODS = [5, 6, 7, 8, 9, 10, 14]  # Różne okresy RSI
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_EXTREME_OVERSOLD = 20
    RSI_EXTREME_OVERBOUGHT = 80
    
    # EMA periods
    EMA_SHORT = 9
    EMA_LONG = 21
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
    BB_SQUEEZE_THRESHOLD = 0.02  # 2% for squeeze detection
    
    # Volume thresholds
    VOLUME_SPIKE_THRESHOLD = 5.0  # 500% wzrost
    VOLUME_SPIKE_EXTREME = 3.0    # 300% powyżej średniej
    
    # Order book parameters
    ORDER_BOOK_DEPTH = 20
    ORDER_BOOK_LEVELS = 5  # L5 depth
    LIQUIDITY_MIN_THRESHOLD = 10000
    ORDER_BOOK_IMBALANCE_THRESHOLD = 0.3
    ORDER_BOOK_EXTREME_IMBALANCE = 0.6
    SPREAD_MULTIPLIER = 2  # Stop-loss = 2× spread
    
    # Market data
    FUNDING_RATE_THRESHOLD = 0.05  # 5% funding rate warning
    OPEN_INTEREST_CHANGE_THRESHOLD = 0.1  # 10% OI change
    
    # Pattern detection
    PATTERNS_ENABLED = True
    PATTERN_CONFIDENCE_THRESHOLD = 0.7
    
    # Sentiment analysis
    SENTIMENT_UPDATE_INTERVAL = 300  # 5 minut
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
    USE_ML_MODELS = False  # Domyślnie wyłączone
    LSTM_LOOKBACK = 60    # Okres lookback dla LSTM
    ENSEMBLE_MODELS = 3   # Liczba modeli w ensemble
    
    # Session timing (UTC)
    ASIAN_SESSION = (0, 8)    # 00:00 - 08:00
    EUROPEAN_SESSION = (7, 16) # 07:00 - 16:00
    US_SESSION = (13, 22)      # 13:00 - 22:00
    HIGH_LIQUIDITY_HOURS = (13, 16)  # Overlap EU/US
    
    # Scalping parameters
    SCALPING_ENABLED = True
    SCALPING_MIN_PROFIT_PERCENT = 0.1
    SCALPING_MAX_HOLD_TIME = 300  # 5 minutes
    
    # System settings
    CHECK_INTERVAL = 30  # Sprawdzanie co 30 sekund
    LOG_LEVEL = 'INFO'
    PAPER_TRADING = True
    
    # Notifications
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # API URLs
    FEAR_GREED_API = "https://api.alternative.me/fng/"
    REDDIT_API = "https://oauth.reddit.com"
    NEWS_API = "https://newsapi.org/v2/everything"