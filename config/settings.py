# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bitget API Keys
    BITGET_API_KEY = os.getenv('BITGET_API_KEY', '')
    BITGET_API_SECRET = os.getenv('BITGET_API_SECRET', '')
    BITGET_PASSPHRASE = os.getenv('BITGET_PASSPHRASE', '')
    
    # Trading parameters dla FUTURES
    TRADING_SYMBOL = 'BTC/USDT:USDT'
    TIMEFRAME = '1m'  # Dane 1-minutowe
    HIGH_FREQUENCY_TIMEFRAME = '1m'  # Zmienione z 15s na 1m
    
    # Futures specific settings
    LEVERAGE = 5
    MARGIN_MODE = 'isolated'
    POSITION_MODE = 'oneway'
    
    # Position sizing
    TRADE_AMOUNT_USDT = 50
    MAX_POSITION_SIZE = 200
    
    # Risk management
    STOP_LOSS_PERCENT = 2.0
    TAKE_PROFIT_PERCENT = 3.0
    MAX_DAILY_LOSS = 100
    MAX_OPEN_POSITIONS = 3
    
    # Entry signals
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    
    # Scalping RSI thresholds
    RSI_EXTREME_OVERSOLD = 25
    RSI_EXTREME_OVERBOUGHT = 75
    
    # Trend filters
    EMA_FAST = 9
    EMA_SLOW = 21
    
    # Volume filter
    MIN_VOLUME_MULTIPLIER = 1.5
    VOLUME_SPIKE_THRESHOLD = 5.0  # 500% wzrost
    VOLUME_EXTREME_THRESHOLD = 3.0  # 300% powyżej średniej
    
    # Order book parameters
    ORDER_BOOK_DEPTH = 20
    SLIPPAGE_THRESHOLD = 0.5
    LIQUIDITY_MIN_THRESHOLD = 10000
    
    # Sentiment analysis parameters
    SENTIMENT_WEIGHT = 0.2
    SENTIMENT_UPDATE_INTERVAL = 300  # Co 5 minut
    
    # System settings
    CHECK_INTERVAL = 30  # Sprawdzanie co 30 sekund dla skalpowania
    LOG_LEVEL = 'INFO'
    
    # Safety
    USE_TESTNET = False
    PAPER_TRADING = True
    
    # Telegram notifications
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Social Media APIs
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN', '')
    CRYPTOPANIC_API_KEY = os.getenv('CRYPTOPANIC_API_KEY', '')
    
    # Scalping Parameters
    SCALPING_ENABLED = True
    SCALPING_MIN_PROFIT_PERCENT = 0.1  # Minimalny zysk 0.1% dla skalpowania
    SCALPING_MAX_HOLD_TIME = 300  # Maksymalny czas trzymania pozycji (5 minut)
    SCALPING_STOP_LOSS = 1.0  # Stop loss 1% dla skalpowania
    SCALPING_TAKE_PROFIT = 1.5  # Take profit 1.5% dla skalpowania
    
    # Order Book Trading Parameters
    ORDER_BOOK_IMBALANCE_THRESHOLD = 0.3
    LARGE_ORDER_MULTIPLIER = 5
    
    # Market Making Parameters
    MARKET_MAKING_ENABLED = False
    MARKET_MAKING_SPREAD = 0.05  # Spread 0.05%
    MARKET_MAKING_SIZE = 10  # Wielkość zlecenia w USDT