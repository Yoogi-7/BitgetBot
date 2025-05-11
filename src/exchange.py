# src/exchange.py
import ccxt
import pandas as pd
import logging
from typing import Dict, List, Optional
from config.settings import Config


class ExchangeConnector:
    """Simplified exchange connection handler."""
    
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
        """Get OHLCV data."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
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
                'volume': float(ticker.get('baseVolume', 0))
            }
        except Exception as e:
            self.logger.error(f"Error fetching ticker: {e}")
            return None
    
    def get_order_book(self, symbol: str = Config.TRADING_SYMBOL, 
                       limit: int = Config.ORDER_BOOK_DEPTH) -> Optional[Dict]:
        """Get order book data."""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            return {
                'bids': orderbook['bids'][:limit],
                'asks': orderbook['asks'][:limit],
                'timestamp': orderbook['timestamp']
            }
        except Exception as e:
            self.logger.error(f"Error fetching order book: {e}")
            return None
    
    def get_recent_trades(self, symbol: str = Config.TRADING_SYMBOL, 
                          limit: int = 50) -> List[Dict]:
        """Get recent trades."""
        try:
            trades = self.exchange.fetch_trades(symbol, limit=limit)
            return [{
                'id': trade.get('id'),
                'timestamp': trade.get('timestamp'),
                'side': trade.get('side'),
                'price': float(trade.get('price', 0)),
                'amount': float(trade.get('amount', 0))
            } for trade in trades]
        except Exception as e:
            self.logger.error(f"Error fetching recent trades: {e}")
            return []
    
    def place_order(self, side: str, amount: float, 
                    order_type: str = 'market', 
                    price: float = None, 
                    reduce_only: bool = False) -> Optional[Dict]:
        """Place an order."""
        try:
            if Config.PAPER_TRADING:
                # Simulate order execution
                ticker = self.get_ticker()
                simulated_price = ticker['last'] if ticker else 0
                
                return {
                    'id': f"paper_{pd.Timestamp.now().timestamp()}",
                    'status': 'closed',
                    'price': simulated_price,
                    'amount': amount,
                    'side': side
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