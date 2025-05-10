# src/data_collector.py
import ccxt
import pandas as pd
from datetime import datetime
import logging
from config.settings import Config

class DataCollector:
    def __init__(self):
        # Konfiguracja dla Bitget
        exchange_config = {
            'apiKey': Config.BITGET_API_KEY,
            'secret': Config.BITGET_API_SECRET,
            'password': Config.BITGET_PASSPHRASE,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # Dla futures perpetual
                'adjustForTimeDifference': True
            }
        }
        
        self.logger = logging.getLogger(__name__)
        self.exchange = ccxt.bitget(exchange_config)
        
        # Testuj połączenie
        self.test_connection()
    
    def test_connection(self):
        """Testuje połączenie z API"""
        try:
            self.exchange.load_markets()
            test_ticker = self.exchange.fetch_ticker('BTC/USDT:USDT')
            self.logger.info(f"Successfully connected to Bitget. BTC Price: {test_ticker['last']}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Bitget: {e}")
            self.logger.error("Please check your API keys and network connection")
    
    def set_leverage(self, symbol=Config.TRADING_SYMBOL, leverage=Config.LEVERAGE):
        """Ustawia dźwignię dla symbolu"""
        try:
            if Config.PAPER_TRADING:
                self.logger.info(f"[PAPER] Would set leverage to {leverage}x for {symbol}")
                return
            
            result = self.exchange.set_leverage(leverage, symbol)
            self.logger.info(f"Leverage set to {leverage}x for {symbol}")
            return result
        except Exception as e:
            self.logger.error(f"Error setting leverage: {e}")
    
    def get_futures_balance(self):
        """Pobiera saldo futures"""
        try:
            if Config.PAPER_TRADING:
                return {
                    'available': 1000.0,
                    'used': 0.0,
                    'total': 1000.0
                }
            
            balance = self.exchange.fetch_balance({'type': 'swap'})
            usdt_balance = balance.get('USDT', {})
            
            return {
                'available': float(usdt_balance.get('free', 0)),
                'used': float(usdt_balance.get('used', 0)),
                'total': float(usdt_balance.get('total', 0))
            }
        except Exception as e:
            self.logger.error(f"Error fetching futures balance: {e}")
            return None
    
    def get_positions(self, symbol=Config.TRADING_SYMBOL):
        """Pobiera otwarte pozycje"""
        try:
            if Config.PAPER_TRADING:
                return []
            
            positions = self.exchange.fetch_positions([symbol])
            open_positions = []
            
            for pos in positions:
                if float(pos.get('contracts', 0)) > 0:
                    open_positions.append({
                        'symbol': pos['symbol'],
                        'side': pos['side'],
                        'size': float(pos['contracts']),
                        'notional': float(pos.get('notional', 0)),
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'mark_price': float(pos.get('markPrice', 0)),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                        'liquidation_price': float(pos.get('liquidationPrice', 0)) if pos.get('liquidationPrice') else None
                    })
            
            return open_positions
        except Exception as e:
            self.logger.error(f"Error fetching positions: {e}")
            return []
    
    def get_high_frequency_data(self, symbol=Config.TRADING_SYMBOL, timeframe='15s', limit=100):
        """Pobiera dane wysokiej częstotliwości (15-sekundowe)"""
        try:
            # Sprawdź czy giełda obsługuje 15s timeframe
            if timeframe == '15s' and '15s' not in self.exchange.timeframes:
                self.logger.warning("15s timeframe not supported, using 1m instead")
                timeframe = '1m'
            
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            self.logger.debug(f"Fetched {len(df)} {timeframe} candles for {symbol}")
            return df
        except Exception as e:
            self.logger.error(f"Error fetching high frequency data: {e}")
            return None
    
    def get_ohlcv_data(self, symbol=Config.TRADING_SYMBOL, timeframe=Config.TIMEFRAME, limit=100):
        """Pobiera dane OHLCV"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            self.logger.debug(f"Fetched {len(df)} candles for {symbol}")
            return df
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data: {e}")
            return None
    
    def get_ticker(self, symbol=Config.TRADING_SYMBOL):
        """Pobiera aktualną cenę"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'last': float(ticker['last']),
                'bid': float(ticker['bid']),
                'ask': float(ticker['ask']),
                'volume': float(ticker.get('baseVolume', 0)),
                'funding_rate': float(ticker.get('fundingRate', 0))
            }
        except Exception as e:
            self.logger.error(f"Error fetching ticker: {e}")
            return None
    
    def get_order_book(self, symbol=Config.TRADING_SYMBOL, limit=20):
        """Pobiera order book"""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            return {
                'bids': orderbook['bids'][:5],
                'asks': orderbook['asks'][:5],
                'timestamp': orderbook['timestamp']
            }
        except Exception as e:
            self.logger.error(f"Error fetching order book: {e}")
            return None