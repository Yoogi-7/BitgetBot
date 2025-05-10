# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bitget API Keys
    BITGET_API_KEY = os.getenv('BITGET_API_KEY', '')
    BITGET_API_SECRET = os.getenv('BITGET_API_SECRET', '')
    BITGET_PASSPHRASE = os.getenv('BITGET_PASSPHRASE', '')  # Bitget wymaga passphrase
    
    # Trading parameters dla FUTURES
    TRADING_SYMBOL = 'BTC/USDT:USDT'  # Symbol dla perpetual futures na Bitget
    TIMEFRAME = '5m'
    
    # Futures specific settings
    LEVERAGE = 5  # Dźwignia 5x (możesz zmienić 1-100)
    MARGIN_MODE = 'isolated'  # 'isolated' lub 'cross'
    POSITION_MODE = 'oneway'  # 'oneway' lub 'hedge'
    
    # Position sizing
    TRADE_AMOUNT_USDT = 50  # Wielkość pozycji w USDT
    MAX_POSITION_SIZE = 200  # Maksymalna pozycja w USDT
    
    # Risk management
    STOP_LOSS_PERCENT = 2.0  # 2% stop loss
    TAKE_PROFIT_PERCENT = 3.0  # 3% take profit
    MAX_DAILY_LOSS = 100  # Maksymalna dzienna strata
    MAX_OPEN_POSITIONS = 3  # Max liczba otwartych pozycji
    
    # Entry signals
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    
    # Trend filters
    EMA_FAST = 9
    EMA_SLOW = 21
    
    # Volume filter
    MIN_VOLUME_MULTIPLIER = 1.5  # Minimalny wolumen vs średnia
    
    # System settings
    CHECK_INTERVAL = 30  # Sprawdzaj co 30 sekund
    LOG_LEVEL = 'INFO'
    
    # Safety
    USE_TESTNET = False  # True = testnet, False = mainnet
    PAPER_TRADING = True  # Jeśli True, tylko symuluje transakcje