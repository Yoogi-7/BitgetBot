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
    HIGH_FREQUENCY_TIMEFRAME = '15s'  # Dla wysokiej częstotliwości
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
    RSI_OVERSOLD = 25
    RSI_OVERBOUGHT = 75
    EMA_FAST = 9
    EMA_SLOW = 21
    ATR_PERIOD = 14
    ATR_PERIOD_SHORT = 5
    
    # Volume thresholds
    VOLUME_SPIKE_THRESHOLD = 5.0  # 500% wzrost
    VOLUME_SPIKE_EXTREME = 3.0    # 300% powyżej średniej
    
    # Order book parameters
    ORDER_BOOK_DEPTH = 20
    ORDER_BOOK_LEVELS = 2  # L2 depth
    LIQUIDITY_MIN_THRESHOLD = 10000
    ORDER_BOOK_IMBALANCE_THRESHOLD = 0.3
    SPREAD_MULTIPLIER = 2  # Stop-loss = 2× spread
    
    # Session timing (UTC)
    ASIAN_SESSION = (0, 8)    # 00:00 - 08:00
    EUROPEAN_SESSION = (7, 16) # 07:00 - 16:00
    US_SESSION = (13, 22)      # 13:00 - 22:00
    HIGH_LIQUIDITY_HOURS = (13, 16)  # Overlap EU/US
    
    # Sentiment analysis
    SENTIMENT_UPDATE_INTERVAL = 300  # 5 minut
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN', '')
    CRYPTOPANIC_API_KEY = os.getenv('CRYPTOPANIC_API_KEY', '')
    
    # Machine Learning
    USE_ML_MODELS = False  # Domyślnie wyłączone
    LSTM_LOOKBACK = 60    # Okres lookback dla LSTM
    ENSEMBLE_MODELS = 3   # Liczba modeli w ensemble
    
    # Scalping parameters
    SCALPING_ENABLED = True
    SCALPING_MIN_PROFIT_PERCENT = 0.1
    SCALPING_MAX_HOLD_TIME = 300  # 5 minutes
    
    # System settings
    CHECK_INTERVAL = 15  # Sprawdzanie co 15 sekund dla wysokiej częstotliwości
    LOG_LEVEL = 'INFO'
    PAPER_TRADING = True
    
    # Notifications
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')