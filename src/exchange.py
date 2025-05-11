# src/exchange.py
import ccxt
import pandas as pd
import logging
from typing import Dict, List, Optional
from config.settings import Config


class ExchangeConnector:
    """Enhanced exchange connection with high-frequency data support."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize exchange
        self.exchange = ccxt.bitget({
            'apiKey': Config.BITGET_API_KEY,
            'secret': Config.BITGET_API_SECRET,
            'password': Config.BITGET_PASSPHRASE,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # For futures
                'adjustForTimeDifference': True
            }
        })
        
        self._test_connection()
    
    def _test_connection(self):
        """Test exchange connection."""
        try:
            self.exchange.load_markets()
            ticker = self.exchange.fetch_ticker(Config.TRADING_SYMBOL)
            self.logger.info(f"Connected to Bitget. BTC Price: {ticker['last']}")
            
            # Check available timeframes
            self.logger.info(f"Available timeframes: {self.exchange.timeframes}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to exchange: {e}")
            raise
    
    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for trading."""
        try:
            if not Config.PAPER_TRADING:
                result = self.exchange.set_leverage(leverage, symbol)
                self.logger.info(f"Leverage set to {leverage}x")
                return result
        except Exception as e:
            self.logger.error(f"Error setting leverage: {e}")
            raise
    
    def get_balance(self) -> Optional[Dict]:
        """Get account balance."""
        try:
            if Config.PAPER_TRADING:
                return {'available': 1000.0, 'used': 0.0, 'total': 1000.0}
            
            balance = self.exchange.fetch_balance({'type': 'swap'})
            usdt_balance = balance.get('USDT', {})
            
            return {
                'available': float(usdt_balance.get('free', 0)),
                'used': float(usdt_balance.get('used', 0)),
                'total': float(usdt_balance.get('total', 0))
            }
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            return None
    
    def get_positions(self) -> List[Dict]:
        """Get open positions."""
        try:
            if Config.PAPER_TRADING:
                return []
            
            positions = self.exchange.fetch_positions([Config.TRADING_SYMBOL])
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
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0))
                    })
            
            return open_positions
        except Exception as e:
            self.logger.error(f"Error fetching positions: {e}")
            return []
    
    def get_ohlcv(self, symbol: str = Config.TRADING_SYMBOL, 
                  timeframe: str = Config.TIMEFRAME, 
                  limit: int = 100) -> Optional[pd.DataFrame]:
        """Get OHLCV data with support for high-frequency timeframes."""
        try:
            # Check if timeframe is supported
            if timeframe not in self.exchange.timeframes:
                # Fallback for unsupported timeframes
                if timeframe == '15s':
                    self.logger.warning(f"Timeframe {timeframe} not supported, using 1m")
                    timeframe = '1m'
                    limit = min(limit, 20)  # Reduce limit for higher frequency
            
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Add derived features for high-frequency analysis
            df['price_change'] = df['close'].pct_change()
            df['volume_change'] = df['volume'].pct_change()
            
            return df
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV: {e}")
            return None
    
    def get_ticker(self, symbol: str = Config.TRADING_SYMBOL) -> Optional[Dict]:
        """Get current ticker information."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'last': float(ticker['last']),
                'bid': float(ticker['bid']),
                'ask': float(ticker['ask']),
                'volume': float(ticker.get('baseVolume', 0)),
                'spread': (float(ticker['ask']) - float(ticker['bid'])) / float(ticker['bid'])
            }
        except Exception as e:
            self.logger.error(f"Error fetching ticker: {e}")
            return None
    
    def get_order_book(self, symbol: str = Config.TRADING_SYMBOL, 
                       limit: int = Config.ORDER_BOOK_DEPTH) -> Optional[Dict]:
        """Get order book data with L2 depth."""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            
            # Process order book for L2 data
            return {
                'bids': orderbook['bids'][:Config.ORDER_BOOK_LEVELS],
                'asks': orderbook['asks'][:Config.ORDER_BOOK_LEVELS],
                'full_bids': orderbook['bids'][:limit],
                'full_asks': orderbook['asks'][:limit],
                'timestamp': orderbook['timestamp']
            }
        except Exception as e:
            self.logger.error(f"Error fetching order book: {e}")
            return None
    
    def get_recent_trades(self, symbol: str = Config.TRADING_SYMBOL, 
                          limit: int = 100) -> List[Dict]:
        """Get recent trades with enhanced data."""
        try:
            trades = self.exchange.fetch_trades(symbol, limit=limit)
            
            processed_trades = []
            for trade in trades:
                processed_trades.append({
                    'id': trade.get('id'),
                    'timestamp': trade.get('timestamp'),
                    'datetime': trade.get('datetime'),
                    'side': trade.get('side'),
                    'price': float(trade.get('price', 0)),
                    'amount': float(trade.get('amount', 0)),
                    'cost': float(trade.get('cost', 0))
                })
            
            return processed_trades
        except Exception as e:
            self.logger.error(f"Error fetching recent trades: {e}")
            return []
    
    def place_order(self, side: str, amount: float, 
                    order_type: str = 'market', 
                    price: float = None, 
                    reduce_only: bool = False) -> Optional[Dict]:
        """Place an order with enhanced error handling."""
        try:
            if Config.PAPER_TRADING:
                # Simulate order execution with slippage
                ticker = self.get_ticker()
                simulated_price = ticker['last'] if ticker else 0
                
                # Add simulated slippage
                if side == 'buy':
                    simulated_price *= 1.0001  # 0.01% slippage
                else:
                    simulated_price *= 0.9999
                
                return {
                    'id': f"paper_{pd.Timestamp.now().timestamp()}",
                    'status': 'closed',
                    'price': simulated_price,
                    'amount': amount,
                    'side': side,
                    'filled': amount,
                    'remaining': 0
                }
            
            params = {'reduceOnly': reduce_only}
            
            if order_type == 'market':
                order = self.exchange.create_market_order(
                    Config.TRADING_SYMBOL, side, amount, params=params
                )
            else:
                order = self.exchange.create_limit_order(
                    Config.TRADING_SYMBOL, side, amount, price, params=params
                )
            
            self.logger.info(f"Order placed: {side} {amount} @ {order.get('price', 'market')}")
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None