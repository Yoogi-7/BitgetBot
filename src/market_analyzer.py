# src/market_analyzer.py
import numpy as np
from typing import Dict, List
from config.settings import Config


class MarketAnalyzer:
    """Combined market analysis (order book + sentiment)."""
    
    def analyze(self, market_data: Dict) -> Dict:
        """Perform comprehensive market analysis."""
        analysis = {}
        
        # Analyze order book
        if market_data.get('order_book'):
            order_book_analysis = self._analyze_order_book(market_data['order_book'])
            analysis.update(order_book_analysis)
        
        # Analyze recent trades
        if market_data.get('recent_trades'):
            trade_flow_analysis = self._analyze_trade_flow(market_data['recent_trades'])
            analysis.update(trade_flow_analysis)
        
        # Basic sentiment (simplified)
        analysis['sentiment'] = self._analyze_basic_sentiment(market_data)
        
        return analysis
    
    def _analyze_order_book(self, order_book: Dict) -> Dict:
        """Analyze order book for imbalances and liquidity."""
        if not order_book or not order_book.get('bids') or not order_book.get('asks'):
            return {'order_book_imbalance': 0, 'spread': 0, 'liquidity': 0}
        
        # Calculate spread
        best_bid = float(order_book['bids'][0][0])
        best_ask = float(order_book['asks'][0][0])
        spread = (best_ask - best_bid) / best_bid * 100
        
        # Calculate order book imbalance
        bid_volume = sum(float(size) for _, size in order_book['bids'][:5])
        ask_volume = sum(float(size) for _, size in order_book['asks'][:5])
        total_volume = bid_volume + ask_volume
        
        imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0
        
        # Calculate liquidity
        bid_liquidity = sum(float(price) * float(size) for price, size in order_book['bids'][:10])
        ask_liquidity = sum(float(price) * float(size) for price, size in order_book['asks'][:10])
        total_liquidity = bid_liquidity + ask_liquidity
        
        return {
            'order_book_imbalance': imbalance,
            'spread': spread,
            'liquidity': total_liquidity,
            'bid_liquidity': bid_liquidity,
            'ask_liquidity': ask_liquidity
        }
    
    def _analyze_trade_flow(self, recent_trades: List[Dict]) -> Dict:
        """Analyze recent trade flow for buy/sell pressure."""
        if not recent_trades:
            return {'buy_pressure': 0, 'sell_pressure': 0, 'net_flow': 0}
        
        buy_volume = sum(trade['amount'] for trade in recent_trades if trade['side'] == 'buy')
        sell_volume = sum(trade['amount'] for trade in recent_trades if trade['side'] == 'sell')
        
        total_volume = buy_volume + sell_volume
        net_flow = buy_volume - sell_volume
        
        return {
            'buy_pressure': buy_volume / total_volume if total_volume > 0 else 0.5,
            'sell_pressure': sell_volume / total_volume if total_volume > 0 else 0.5,
            'net_flow': net_flow,
            'trade_imbalance': net_flow / total_volume if total_volume > 0 else 0
        }
    
    def _analyze_basic_sentiment(self, market_data: Dict) -> str:
        """Basic market sentiment analysis."""
        # Simple sentiment based on price action and volume
        if 'ohlcv' in market_data and not market_data['ohlcv'].empty:
            df = market_data['ohlcv']
            
            # Recent price change
            price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
            
            # Volume trend
            recent_volume = df['volume'].iloc[-5:].mean()
            older_volume = df['volume'].iloc[-10:-5].mean()
            volume_trend = (recent_volume - older_volume) / older_volume if older_volume > 0 else 0
            
            # Determine sentiment
            if price_change > 0.01 and volume_trend > 0.2:
                return 'bullish'
            elif price_change < -0.01 and volume_trend > 0.2:
                return 'bearish'
            else:
                return 'neutral'
        
        return 'neutral'