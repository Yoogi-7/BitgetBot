# src/market_analyzer.py
import numpy as np
import requests
from typing import Dict, List
from datetime import datetime, timedelta
from config.settings import Config


class MarketAnalyzer:
    """Enhanced market analysis with order book, sentiment, and ML integration."""
    
    def __init__(self):
        self.last_sentiment_update = 0
        self.cached_sentiment = {'sentiment': 'neutral', 'score': 0}
        self.ml_predictor = None
        
        # Initialize ML if enabled
        if Config.USE_ML_MODELS:
            try:
                from src.ml_models import MLPredictor
                self.ml_predictor = MLPredictor(use_ml=True)
            except ImportError:
                pass
    
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
        
        # Analyze sentiment
        sentiment_analysis = self._analyze_sentiment()
        analysis.update(sentiment_analysis)
        
        # ML predictions if available
        if self.ml_predictor and Config.USE_ML_MODELS:
            ml_analysis = self._get_ml_predictions(market_data)
            analysis.update(ml_analysis)
        
        return analysis
    
    def _analyze_order_book(self, order_book: Dict) -> Dict:
        """Enhanced order book analysis with L2 depth and slippage calculation."""
        if not order_book or not order_book.get('bids') or not order_book.get('asks'):
            return {
                'order_book_imbalance': 0, 
                'spread': 0, 
                'liquidity': 0,
                'slippage_estimate': 0
            }
        
        # L2 data (top levels)
        l2_bids = order_book.get('bids', [])[:Config.ORDER_BOOK_LEVELS]
        l2_asks = order_book.get('asks', [])[:Config.ORDER_BOOK_LEVELS]
        
        # Calculate spread
        best_bid = float(l2_bids[0][0]) if l2_bids else 0
        best_ask = float(l2_asks[0][0]) if l2_asks else 0
        spread = (best_ask - best_bid) / best_bid * 100 if best_bid > 0 else 0
        
        # Calculate order book imbalance for L2
        bid_volume_l2 = sum(float(size) for _, size in l2_bids)
        ask_volume_l2 = sum(float(size) for _, size in l2_asks)
        total_volume_l2 = bid_volume_l2 + ask_volume_l2
        imbalance_l2 = (bid_volume_l2 - ask_volume_l2) / total_volume_l2 if total_volume_l2 > 0 else 0
        
        # Full order book analysis
        full_bids = order_book.get('full_bids', [])[:Config.ORDER_BOOK_DEPTH]
        full_asks = order_book.get('full_asks', [])[:Config.ORDER_BOOK_DEPTH]
        
        # Calculate liquidity
        bid_liquidity = sum(float(price) * float(size) for price, size in full_bids)
        ask_liquidity = sum(float(price) * float(size) for price, size in full_asks)
        total_liquidity = bid_liquidity + ask_liquidity
        
        # Calculate slippage for standard trade size
        slippage_estimate = self._calculate_slippage(
            full_asks, 
            Config.TRADE_AMOUNT_USDT, 
            'buy'
        )
        
        return {
            'order_book_imbalance': imbalance_l2,
            'spread': spread,
            'spread_bps': spread * 100,  # Spread in basis points
            'liquidity': total_liquidity,
            'bid_liquidity': bid_liquidity,
            'ask_liquidity': ask_liquidity,
            'liquidity_ratio': bid_liquidity / ask_liquidity if ask_liquidity > 0 else 1,
            'slippage_estimate': slippage_estimate,
            'l2_depth': {
                'bid_volume': bid_volume_l2,
                'ask_volume': ask_volume_l2
            }
        }
    
    def _calculate_slippage(self, orders: List, trade_size_usd: float, side: str) -> float:
        """Calculate expected slippage for a given trade size."""
        if not orders:
            return 0
        
        remaining_size = trade_size_usd
        total_cost = 0
        filled_size = 0
        
        for price, size in orders:
            price = float(price)
            size = float(size)
            order_value = price * size
            
            if remaining_size <= 0:
                break
            
            if order_value >= remaining_size:
                # Partial fill
                filled_amount = remaining_size / price
                total_cost += remaining_size
                filled_size += filled_amount
                remaining_size = 0
            else:
                # Full fill of this level
                total_cost += order_value
                filled_size += size
                remaining_size -= order_value
        
        if filled_size == 0:
            return 0
        
        avg_price = total_cost / filled_size
        best_price = float(orders[0][0])
        slippage = abs(avg_price - best_price) / best_price
        
        return slippage
    
    def _analyze_trade_flow(self, recent_trades: List[Dict]) -> Dict:
        """Analyze recent trade flow for momentum and aggression."""
        if not recent_trades:
            return {
                'buy_pressure': 0.5, 
                'sell_pressure': 0.5, 
                'net_flow': 0,
                'trade_aggression': 0
            }
        
        # Separate buy and sell trades
        buy_trades = [t for t in recent_trades if t['side'] == 'buy']
        sell_trades = [t for t in recent_trades if t['side'] == 'sell']
        
        # Calculate volumes
        buy_volume = sum(trade['amount'] for trade in buy_trades)
        sell_volume = sum(trade['amount'] for trade in sell_trades)
        total_volume = buy_volume + sell_volume
        
        # Calculate trade sizes for aggression metric
        buy_sizes = [trade['amount'] for trade in buy_trades]
        sell_sizes = [trade['amount'] for trade in sell_trades]
        
        avg_buy_size = np.mean(buy_sizes) if buy_sizes else 0
        avg_sell_size = np.mean(sell_sizes) if sell_sizes else 0
        
        # Trade aggression (larger trades indicate more aggressive traders)
        overall_avg_size = np.mean([t['amount'] for t in recent_trades])
        trade_aggression = max(avg_buy_size, avg_sell_size) / overall_avg_size if overall_avg_size > 0 else 1
        
        net_flow = buy_volume - sell_volume
        
        return {
            'buy_pressure': buy_volume / total_volume if total_volume > 0 else 0.5,
            'sell_pressure': sell_volume / total_volume if total_volume > 0 else 0.5,
            'net_flow': net_flow,
            'trade_imbalance': net_flow / total_volume if total_volume > 0 else 0,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'trade_aggression': trade_aggression,
            'avg_buy_size': avg_buy_size,
            'avg_sell_size': avg_sell_size
        }
    
    def _analyze_sentiment(self) -> Dict:
        """Analyze market sentiment from multiple sources."""
        current_time = datetime.now().timestamp()
        
        # Update sentiment if needed
        if current_time - self.last_sentiment_update > Config.SENTIMENT_UPDATE_INTERVAL:
            self.cached_sentiment = self._fetch_sentiment()
            self.last_sentiment_update = current_time
        
        return self.cached_sentiment
    
    def _fetch_sentiment(self) -> Dict:
        """Fetch sentiment from CryptoPanic and other sources."""
        sentiment_data = {
            'sentiment': 'neutral',
            'score': 0,
            'sources': {}
        }
        
        # CryptoPanic sentiment
        if Config.CRYPTOPANIC_API_KEY:
            cryptopanic_sentiment = self._get_cryptopanic_sentiment()
            sentiment_data['sources']['cryptopanic'] = cryptopanic_sentiment
        
        # Twitter sentiment (simplified without API)
        # In production, you would use Twitter API
        sentiment_data['sources']['social'] = {'sentiment': 'neutral', 'score': 0}
        
        # Calculate overall sentiment
        scores = []
        for source, data in sentiment_data['sources'].items():
            if 'score' in data:
                scores.append(data['score'])
        
        if scores:
            avg_score = np.mean(scores)
            sentiment_data['score'] = avg_score
            
            if avg_score > 0.2:
                sentiment_data['sentiment'] = 'bullish'
            elif avg_score < -0.2:
                sentiment_data['sentiment'] = 'bearish'
            else:
                sentiment_data['sentiment'] = 'neutral'
        
        return sentiment_data
    
    def _get_cryptopanic_sentiment(self) -> Dict:
        """Get sentiment from CryptoPanic API."""
        try:
            url = "https://cryptopanic.com/api/v1/posts/"
            params = {
                'auth_token': Config.CRYPTOPANIC_API_KEY,
                'currencies': 'BTC',
                'filter': 'rising',
                'public': 'true'
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if 'results' not in data:
                return {'sentiment': 'neutral', 'score': 0}
            
            # Analyze sentiment from votes
            positive_votes = 0
            negative_votes = 0
            
            for post in data['results'][:20]:  # Analyze top 20 posts
                votes = post.get('votes', {})
                positive_votes += votes.get('positive', 0)
                negative_votes += votes.get('negative', 0)
            
            total_votes = positive_votes + negative_votes
            
            if total_votes > 0:
                sentiment_score = (positive_votes - negative_votes) / total_votes
                
                if sentiment_score > 0.2:
                    return {'sentiment': 'bullish', 'score': sentiment_score}
                elif sentiment_score < -0.2:
                    return {'sentiment': 'bearish', 'score': sentiment_score}
            
            return {'sentiment': 'neutral', 'score': 0}
            
        except Exception as e:
            return {'sentiment': 'neutral', 'score': 0, 'error': str(e)}
    
    def _get_ml_predictions(self, market_data: Dict) -> Dict:
        """Get ML model predictions if available."""
        if not self.ml_predictor:
            return {'ml_signal': 'none', 'ml_confidence': 0}
        
        try:
            # Get current indicators from strategy
            from src.strategy import TradingStrategy
            strategy = TradingStrategy()
            df = market_data.get('ohlcv')
            
            if df is not None:
                strategy._calculate_indicators(df)
                ml_prediction = self.ml_predictor.predict(market_data, strategy.indicators)
                
                return {
                    'ml_signal': ml_prediction.get('ml_signal', 'none'),
                    'ml_confidence': ml_prediction.get('confidence', 0)
                }
        except Exception as e:
            return {'ml_signal': 'error', 'ml_confidence': 0, 'ml_error': str(e)}
        
        return {'ml_signal': 'none', 'ml_confidence': 0}