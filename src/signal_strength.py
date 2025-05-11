# src/signal_strength.py
import numpy as np
from typing import Dict, List
from config.settings import Config


class SignalStrengthCalculator:
    """Calculate signal strength based on multiple indicators correlation."""
    
    def __init__(self):
        # Weights for different indicator categories
        self.category_weights = {
            'trend': 0.25,
            'momentum': 0.25,
            'volatility': 0.15,
            'volume': 0.15,
            'pattern': 0.10,
            'sentiment': 0.10
        }
        
        # Individual indicator weights within categories
        self.indicator_weights = {
            # Trend indicators
            'ema_crossover': 0.4,
            'trend_strength': 0.3,
            'vwap_position': 0.3,
            
            # Momentum indicators
            'rsi': 0.3,
            'macd': 0.3,
            'stochastic': 0.2,
            'rate_of_change': 0.2,
            
            # Volatility indicators
            'bb_position': 0.4,
            'bb_squeeze': 0.3,
            'atr_trend': 0.3,
            
            # Volume indicators
            'volume_spike': 0.4,
            'volume_trend': 0.3,
            'order_book_imbalance': 0.3,
            
            # Pattern indicators
            'candlestick_pattern': 0.5,
            'chart_pattern': 0.5,
            
            # Sentiment indicators
            'market_sentiment': 0.6,
            'news_sentiment': 0.4
        }
    
    def calculate_signal_strength(self, signals: Dict, market_data: Dict, 
                                sentiment: Dict) -> Dict:
        """Calculate overall signal strength from 0-100."""
        scores = {
            'trend': self._calculate_trend_score(signals, market_data),
            'momentum': self._calculate_momentum_score(signals),
            'volatility': self._calculate_volatility_score(signals),
            'volume': self._calculate_volume_score(signals, market_data),
            'pattern': self._calculate_pattern_score(signals),
            'sentiment': self._calculate_sentiment_score(sentiment, signals)
        }
        
        # Calculate weighted total
        total_score = 0
        for category, score in scores.items():
            weight = self.category_weights.get(category, 0)
            total_score += score * weight
        
        # Apply sentiment penalty if misaligned
        sentiment_penalty = self._calculate_sentiment_penalty(sentiment, signals)
        total_score -= sentiment_penalty
        
        # Ensure score is between 0 and 100
        total_score = max(0, min(100, total_score))
        
        return {
            'total_score': total_score,
            'category_scores': scores,
            'sentiment_penalty': sentiment_penalty,
            'strength_level': self._get_strength_level(total_score),
            'sentiment_aligned': sentiment_penalty == 0
        }
    
    def _calculate_trend_score(self, signals: Dict, market_data: Dict) -> float:
        """Calculate trend strength score."""
        score = 0
        weights_sum = 0
        
        # EMA crossover
        if signals.get('ema_crossover'):
            crossover_score = 100 if signals['ema_crossover'] != 'none' else 0
            score += crossover_score * self.indicator_weights['ema_crossover']
            weights_sum += self.indicator_weights['ema_crossover']
        
        # Trend strength
        if signals.get('trend'):
            trend_scores = {
                'strong_bullish': 100,
                'bullish': 75,
                'neutral': 50,
                'bearish': 25,
                'strong_bearish': 0
            }
            trend_score = trend_scores.get(signals['trend'], 50)
            score += trend_score * self.indicator_weights['trend_strength']
            weights_sum += self.indicator_weights['trend_strength']
        
        # VWAP position
        if signals.get('vwap') and market_data.get('ticker'):
            price = market_data['ticker']['last']
            vwap = signals['vwap']
            vwap_ratio = (price - vwap) / vwap
            
            # Convert to score (above VWAP is bullish)
            vwap_score = 50 + (vwap_ratio * 1000)  # Scale it
            vwap_score = max(0, min(100, vwap_score))
            
            score += vwap_score * self.indicator_weights['vwap_position']
            weights_sum += self.indicator_weights['vwap_position']
        
        return (score / weights_sum * 100) if weights_sum > 0 else 50
    
    def _calculate_momentum_score(self, signals: Dict) -> float:
        """Calculate momentum score."""
        score = 0
        weights_sum = 0
        
        # RSI
        if signals.get('rsi_14') is not None:
            rsi = signals['rsi_14']
            # Convert RSI to bullish/bearish score
            if rsi < 30:
                rsi_score = 100  # Oversold - bullish
            elif rsi > 70:
                rsi_score = 0    # Overbought - bearish
            else:
                rsi_score = 50 + (50 - rsi) * (50/40)  # Linear scale
            
            score += rsi_score * self.indicator_weights['rsi']
            weights_sum += self.indicator_weights['rsi']
        
        # MACD
        if signals.get('macd_divergence'):
            divergence_scores = {
                'bullish': 90,
                'bearish': 10,
                'none': 50
            }
            macd_score = divergence_scores.get(signals['macd_divergence'], 50)
            score += macd_score * self.indicator_weights['macd']
            weights_sum += self.indicator_weights['macd']
        
        return (score / weights_sum * 100) if weights_sum > 0 else 50
    
    def _calculate_volatility_score(self, signals: Dict) -> float:
        """Calculate volatility score."""
        score = 0
        weights_sum = 0
        
        # Bollinger Bands position
        if signals.get('bb_position'):
            position_scores = {
                'below': 80,   # Below lower band - oversold
                'inside': 50,  # Inside bands - neutral
                'above': 20    # Above upper band - overbought
            }
            bb_score = position_scores.get(signals['bb_position'], 50)
            score += bb_score * self.indicator_weights['bb_position']
            weights_sum += self.indicator_weights['bb_position']
        
        # Bollinger Bands squeeze
        if signals.get('bb_squeeze'):
            squeeze_score = 80 if signals['bb_squeeze'] else 50
            score += squeeze_score * self.indicator_weights['bb_squeeze']
            weights_sum += self.indicator_weights['bb_squeeze']
        
        return (score / weights_sum * 100) if weights_sum > 0 else 50
    
    def _calculate_volume_score(self, signals: Dict, market_data: Dict) -> float:
        """Calculate volume score."""
        score = 0
        weights_sum = 0
        
        # Volume spike
        if signals.get('volume_spike'):
            spike_score = 80 if signals['volume_spike'] else 50
            score += spike_score * self.indicator_weights['volume_spike']
            weights_sum += self.indicator_weights['volume_spike']
        
        # Volume trend
        if signals.get('volume_trend'):
            trend_scores = {
                'increasing': 70,
                'decreasing': 30,
                'neutral': 50
            }
            volume_trend_score = trend_scores.get(signals['volume_trend'], 50)
            score += volume_trend_score * self.indicator_weights['volume_trend']
            weights_sum += self.indicator_weights['volume_trend']
        
        # Order book imbalance
        if market_data.get('order_book', {}).get('imbalance'):
            imbalance = market_data['order_book']['imbalance']['level_5']['imbalance']
            # Convert imbalance to score (-1 to 1 -> 0 to 100)
            imbalance_score = (imbalance + 1) * 50
            score += imbalance_score * self.indicator_weights['order_book_imbalance']
            weights_sum += self.indicator_weights['order_book_imbalance']
        
        return (score / weights_sum * 100) if weights_sum > 0 else 50
    
    def _calculate_pattern_score(self, signals: Dict) -> float:
        """Calculate pattern recognition score."""
        score = 0
        weights_sum = 0
        
        # Candlestick patterns
        pattern_scores = {
            'bullish': 80,
            'bearish': 20,
            'none': 50
        }
        
        for pattern_type in ['pattern_engulfing', 'pattern_pin_bar', 'pattern_breakout']:
            if signals.get(pattern_type):
                pattern_score = pattern_scores.get(signals[pattern_type], 50)
                score += pattern_score * self.indicator_weights['candlestick_pattern']
                weights_sum += self.indicator_weights['candlestick_pattern']
        
        return (score / weights_sum * 100) if weights_sum > 0 else 50
    
    def _calculate_sentiment_score(self, sentiment: Dict, signals: Dict) -> float:
        """Calculate sentiment score."""
        if not sentiment:
            return 50
        
        sentiment_scores = {
            'bullish': 70,
            'bearish': 30,
            'neutral': 50
        }
        
        overall_sentiment = sentiment.get('overall_sentiment', 'neutral')
        return sentiment_scores.get(overall_sentiment, 50)
    
    def _calculate_sentiment_penalty(self, sentiment: Dict, signals: Dict) -> float:
        """Calculate penalty for sentiment misalignment."""
        if not Config.SENTIMENT_ALIGNMENT_REQUIRED or not sentiment:
            return 0
        
        signal_direction = self._get_signal_direction(signals)
        sentiment_direction = sentiment.get('overall_sentiment', 'neutral')
        
        # Check if misaligned
        if signal_direction == 'bullish' and sentiment_direction == 'bearish':
            return Config.SENTIMENT_DISAGREEMENT_PENALTY
        elif signal_direction == 'bearish' and sentiment_direction == 'bullish':
            return Config.SENTIMENT_DISAGREEMENT_PENALTY
        
        return 0
    
    def _get_signal_direction(self, signals: Dict) -> str:
        """Determine overall signal direction."""
        bullish_count = 0
        bearish_count = 0
        
        # Count directional signals
        direction_indicators = {
            'ema_crossover': signals.get('ema_crossover'),
            'macd_divergence': signals.get('macd_divergence'),
            'pattern_engulfing': signals.get('pattern_engulfing'),
            'trend': signals.get('trend')
        }
        
        for indicator, value in direction_indicators.items():
            if value in ['bullish', 'strong_bullish']:
                bullish_count += 1
            elif value in ['bearish', 'strong_bearish']:
                bearish_count += 1
        
        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'
    
    def _get_strength_level(self, score: float) -> str:
        """Get strength level description."""
        if score >= Config.STRONG_SIGNAL_THRESHOLD:
            return 'strong'
        elif score >= Config.MIN_SIGNAL_STRENGTH:
            return 'medium'
        elif score >= Config.WEAK_SIGNAL_THRESHOLD:
            return 'weak'
        else:
            return 'very_weak'