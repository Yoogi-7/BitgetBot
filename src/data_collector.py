# src/data_collector.py
import ccxt
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional
from config.settings import Config
from src.indicators import TechnicalIndicators


class EnhancedDataCollector:
    """Enhanced data collection with funding rate, open interest, and multi-timeframe support."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.exchange = None
        self.indicators = TechnicalIndicators()
        self._initialize_exchange()
    
    def _initialize_exchange(self):
        """Initialize exchange connection."""
        self.exchange = ccxt.bitget({
            'apiKey': Config.BITGET_API_KEY,
            'secret': Config.BITGET_API_SECRET,
            'password': Config.BITGET_PASSPHRASE,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
                'adjustForTimeDifference': True
            }
        })
        
        try:
            self.exchange.load_markets()
            self.logger.info("Exchange initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize exchange: {e}")
            raise
    
    def collect_comprehensive_data(self, symbol: str = Config.TRADING_SYMBOL) -> Dict:
        """Collect all required market data."""
        try:
            data = {
                'symbol': symbol,
                'timestamp': pd.Timestamp.now(),
                'timeframes': {}
            }
            
            # Collect OHLCV data for multiple timeframes
            for timeframe in Config.TIMEFRAMES:
                ohlcv = self.get_ohlcv_data(symbol, timeframe)
                if ohlcv is not None:
                    # Calculate indicators for each timeframe
                    indicators = self.indicators.calculate_all_indicators(ohlcv)
                    data['timeframes'][timeframe] = {
                        'ohlcv': ohlcv,
                        'indicators': indicators.copy()
                    }
            
            # Get current market data
            data['ticker'] = self.get_ticker(symbol)
            data['order_book'] = self.get_order_book(symbol)
            data['recent_trades'] = self.get_recent_trades(symbol)
            
            # Get derivatives data
            data['funding_rate'] = self.get_funding_rate(symbol)
            data['open_interest'] = self.get_open_interest(symbol)
            
            # Calculate additional market metrics
            data['market_metrics'] = self._calculate_market_metrics(data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error collecting comprehensive data: {e}")
            return None
    
    def get_ohlcv_data(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Get OHLCV data for specified timeframe."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data: {e}")
            return None
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get current ticker information."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'last': float(ticker['last']),
                'bid': float(ticker['bid']),
                'ask': float(ticker['ask']),
                'volume': float(ticker.get('baseVolume', 0)),
                'quote_volume': float(ticker.get('quoteVolume', 0)),
                'change_24h': float(ticker.get('change', 0)),
                'percentage_24h': float(ticker.get('percentage', 0)),
                'vwap': float(ticker.get('vwap', 0)),
                'spread': (float(ticker['ask']) - float(ticker['bid'])) / float(ticker['bid'])
            }
        except Exception as e:
            self.logger.error(f"Error fetching ticker: {e}")
            return None
    
    def get_order_book(self, symbol: str, limit: int = Config.ORDER_BOOK_DEPTH) -> Optional[Dict]:
        """Get order book data with L5 depth."""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            
            # Process order book for multiple levels
            return {
                'bids': orderbook['bids'][:Config.ORDER_BOOK_LEVELS],
                'asks': orderbook['asks'][:Config.ORDER_BOOK_LEVELS],
                'full_bids': orderbook['bids'][:limit],
                'full_asks': orderbook['asks'][:limit],
                'timestamp': orderbook['timestamp'],
                'l1': {
                    'bid': float(orderbook['bids'][0][0]) if orderbook['bids'] else 0,
                    'ask': float(orderbook['asks'][0][0]) if orderbook['asks'] else 0,
                    'bid_size': float(orderbook['bids'][0][1]) if orderbook['bids'] else 0,
                    'ask_size': float(orderbook['asks'][0][1]) if orderbook['asks'] else 0,
                },
                'imbalance': self._calculate_order_book_imbalance(orderbook)
            }
        except Exception as e:
            self.logger.error(f"Error fetching order book: {e}")
            return None
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
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
                    'cost': float(trade.get('cost', 0)),
                    'takerOrMaker': trade.get('takerOrMaker')
                })
            
            return processed_trades
        except Exception as e:
            self.logger.error(f"Error fetching recent trades: {e}")
            return []
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """Get funding rate information."""
        try:
            # This is exchange-specific, adjust for Bitget
            funding = self.exchange.fetch_funding_rate(symbol)
            
            return {
                'current': float(funding.get('fundingRate', 0)),
                'next': float(funding.get('nextFundingRate', 0)),
                'timestamp': funding.get('timestamp'),
                'funding_timestamp': funding.get('fundingTimestamp')
            }
        except Exception as e:
            self.logger.error(f"Error fetching funding rate: {e}")
            # Fallback to manual API call if needed
            try:
                # Alternative method for Bitget
                url = f"{self.exchange.urls['api']['public']}/market/funding_rate"
                response = self.exchange.fetch(url, params={'symbol': symbol})
                if response and 'data' in response:
                    data = response['data']
                    return {
                        'current': float(data.get('fundingRate', 0)),
                        'next': float(data.get('nextFundingRate', 0)),
                        'timestamp': pd.Timestamp.now()
                    }
            except:
                pass
            
            return None
    
    def get_open_interest(self, symbol: str) -> Optional[Dict]:
        """Get open interest data."""
        try:
            # Get open interest data
            oi_data = self.exchange.fetch_open_interest(symbol)
            
            # Calculate 24h change if historical data available
            oi_history = self.exchange.fetch_open_interest_history(symbol, limit=24)
            
            current_oi = float(oi_data.get('openInterest', 0))
            oi_24h_ago = float(oi_history[0].get('openInterest', 0)) if oi_history else current_oi
            
            oi_change = (current_oi - oi_24h_ago) / oi_24h_ago if oi_24h_ago > 0 else 0
            
            return {
                'current': current_oi,
                'value_usd': float(oi_data.get('openInterestValue', 0)),
                'change_24h': oi_change,
                'change_percent_24h': oi_change * 100,
                'timestamp': pd.Timestamp.now()
            }
        except Exception as e:
            self.logger.error(f"Error fetching open interest: {e}")
            return None
    
    def _calculate_order_book_imbalance(self, orderbook: Dict) -> Dict:
        """Calculate detailed order book imbalance metrics."""
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            # Calculate imbalance for different levels
            imbalances = {}
            
            for level in [1, 5, 10, 20]:
                bid_volume = sum(float(size) for _, size in bids[:level])
                ask_volume = sum(float(size) for _, size in asks[:level])
                total_volume = bid_volume + ask_volume
                
                if total_volume > 0:
                    imbalance = (bid_volume - ask_volume) / total_volume
                    imbalances[f'level_{level}'] = {
                        'imbalance': imbalance,
                        'bid_volume': bid_volume,
                        'ask_volume': ask_volume,
                        'ratio': bid_volume / ask_volume if ask_volume > 0 else float('inf')
                    }
            
            # Detect extreme imbalances
            if abs(imbalances.get('level_5', {}).get('imbalance', 0)) > Config.ORDER_BOOK_EXTREME_IMBALANCE:
                imbalances['extreme_imbalance'] = True
            else:
                imbalances['extreme_imbalance'] = False
            
            return imbalances
            
        except Exception as e:
            self.logger.error(f"Error calculating order book imbalance: {e}")
            return {}
    
    def _calculate_market_metrics(self, data: Dict) -> Dict:
        """Calculate additional market metrics from collected data."""
        metrics = {}
        
        try:
            # Funding rate analysis
            funding = data.get('funding_rate', {})
            if funding:
                metrics['funding_extreme'] = abs(funding.get('current', 0)) > Config.FUNDING_RATE_THRESHOLD
                metrics['funding_direction'] = 'long' if funding.get('current', 0) > 0 else 'short'
            
            # Open interest analysis
            oi = data.get('open_interest', {})
            if oi:
                metrics['oi_increasing'] = oi.get('change_percent_24h', 0) > Config.OPEN_INTEREST_CHANGE_THRESHOLD
                metrics['oi_decreasing'] = oi.get('change_percent_24h', 0) < -Config.OPEN_INTEREST_CHANGE_THRESHOLD
            
            # Multi-timeframe analysis
            if data.get('timeframes'):
                # Check for trend alignment across timeframes
                trends = []
                for tf, tf_data in data['timeframes'].items():
                    trend = tf_data.get('indicators', {}).get('trend')
                    if trend:
                        trends.append(trend)
                
                # Check if all timeframes show same trend
                if trends and all(t == trends[0] for t in trends):
                    metrics['trend_aligned'] = True
                    metrics['aligned_trend'] = trends[0]
                else:
                    metrics['trend_aligned'] = False
                
                # Check for pattern confluence
                patterns = []
                for tf, tf_data in data['timeframes'].items():
                    indicators = tf_data.get('indicators', {})
                    if indicators.get('pattern_engulfing') != 'none':
                        patterns.append(indicators['pattern_engulfing'])
                    if indicators.get('pattern_pin_bar') != 'none':
                        patterns.append(indicators['pattern_pin_bar'])
                
                metrics['pattern_confluence'] = len(set(patterns)) >= 2
            
            # Market strength score
            strength_score = 0
            
            # Add points for various conditions
            if metrics.get('trend_aligned'):
                strength_score += 2
            
            if data.get('order_book', {}).get('imbalance', {}).get('level_5', {}).get('imbalance', 0) > 0.3:
                strength_score += 1
            
            if data.get('timeframes', {}).get('1m', {}).get('indicators', {}).get('volume_spike'):
                strength_score += 1
            
            metrics['market_strength'] = strength_score
            
        except Exception as e:
            self.logger.error(f"Error calculating market metrics: {e}")
        
        return metrics