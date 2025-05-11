# src/strategy.py
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from config.settings import Config
from src.indicators import TechnicalIndicators
from src.sentiment_analyzer import EnhancedSentimentAnalyzer


class EnhancedTradingStrategy:
    """Enhanced trading strategy with comprehensive indicators and patterns."""
    
    def __init__(self):
        self.indicators_calculator = TechnicalIndicators()
        self.sentiment_analyzer = EnhancedSentimentAnalyzer()
        self.signal_confirmations = {}
    
    def generate_signal(self, market_data: Dict, positions: List[Dict]) -> Dict:
        """Generate trading signal based on comprehensive data."""
        signal = {
            'action': None,
            'side': None,
            'reason': '',
            'entry_price': 0,
            'stop_loss': None,
            'take_profit': None,
            'confidence': 0.0,
            'confirmations': [],
            'timeframe': Config.DEFAULT_TIMEFRAME
        }
        
        # Skip if max positions reached
        if len(positions) >= Config.MAX_OPEN_POSITIONS:
            return signal
        
        # Get primary timeframe data
        primary_tf = market_data['timeframes'].get(Config.DEFAULT_TIMEFRAME)
        if not primary_tf:
            return signal
        
        indicators = primary_tf['indicators']
        current_price = primary_tf['ohlcv']['close'].iloc[-1]
        signal['entry_price'] = current_price
        
        # Check for exit signals first
        exit_signal = self._check_exit_conditions(positions, market_data)
        if exit_signal:
            return exit_signal
        
        # Analyze multi-timeframe confluence
        mtf_analysis = self._analyze_multi_timeframe(market_data)
        
        # Get sentiment analysis
        sentiment = self.sentiment_analyzer.get_comprehensive_sentiment()
        
        # Check for entry conditions
        entry_signal = self._check_entry_conditions(
            indicators, 
            market_data, 
            mtf_analysis, 
            sentiment,
            positions
        )
        
        if entry_signal:
            return entry_signal
        
        return signal
    
    def _check_entry_conditions(self, indicators: Dict, market_data: Dict, 
                              mtf_analysis: Dict, sentiment: Dict, 
                              positions: List[Dict]) -> Dict:
        """Check for entry conditions with multiple confirmations."""
        confirmations = []
        long_score = 0
        short_score = 0
        
        # 1. Check RSI conditions
        rsi_signal = self._check_rsi_signal(indicators)
        if rsi_signal:
            confirmations.append(rsi_signal)
            if rsi_signal['direction'] == 'bullish':
                long_score += rsi_signal['strength']
            else:
                short_score += rsi_signal['strength']
        
        # 2. Check EMA crossover
        ema_signal = self._check_ema_crossover(indicators)
        if ema_signal:
            confirmations.append(ema_signal)
            if ema_signal['direction'] == 'bullish':
                long_score += ema_signal['strength']
            else:
                short_score += ema_signal['strength']
        
        # 3. Check Bollinger Bands
        bb_signal = self._check_bollinger_bands(indicators)
        if bb_signal:
            confirmations.append(bb_signal)
            if bb_signal['direction'] == 'bullish':
                long_score += bb_signal['strength']
            else:
                short_score += bb_signal['strength']
        
        # 4. Check MACD
        macd_signal = self._check_macd(indicators)
        if macd_signal:
            confirmations.append(macd_signal)
            if macd_signal['direction'] == 'bullish':
                long_score += macd_signal['strength']
            else:
                short_score += macd_signal['strength']
        
        # 5. Check candlestick patterns
        pattern_signal = self._check_patterns(indicators)
        if pattern_signal:
            confirmations.append(pattern_signal)
            if pattern_signal['direction'] == 'bullish':
                long_score += pattern_signal['strength']
            else:
                short_score += pattern_signal['strength']
        
        # 6. Check order book imbalance
        orderbook_signal = self._check_order_book(market_data)
        if orderbook_signal:
            confirmations.append(orderbook_signal)
            if orderbook_signal['direction'] == 'bullish':
                long_score += orderbook_signal['strength']
            else:
                short_score += orderbook_signal['strength']
        
        # 7. Check volume
        volume_signal = self._check_volume(indicators)
        if volume_signal:
            confirmations.append(volume_signal)
            # Volume adds to both directions as confirmation
            long_score += volume_signal['strength'] * 0.5
            short_score += volume_signal['strength'] * 0.5
        
        # 8. Check multi-timeframe alignment
        if mtf_analysis['aligned']:
            mtf_signal = {
                'type': 'mtf_alignment',
                'direction': mtf_analysis['direction'],
                'strength': 0.2,
                'description': f"Multi-timeframe {mtf_analysis['direction']} alignment"
            }
            confirmations.append(mtf_signal)
            if mtf_signal['direction'] == 'bullish':
                long_score += mtf_signal['strength']
            else:
                short_score += mtf_signal['strength']
        
        # 9. Check sentiment
        if sentiment['overall_sentiment'] != 'neutral':
            sentiment_signal = {
                'type': 'sentiment',
                'direction': sentiment['overall_sentiment'],
                'strength': 0.15,
                'description': f"Market sentiment {sentiment['overall_sentiment']}"
            }
            confirmations.append(sentiment_signal)
            if sentiment_signal['direction'] == 'bullish':
                long_score += sentiment_signal['strength']
            else:
                short_score += sentiment_signal['strength']
        
        # 10. Check funding and OI
        funding_signal = self._check_funding_oi(market_data)
        if funding_signal:
            confirmations.append(funding_signal)
            if funding_signal['direction'] == 'bullish':
                long_score += funding_signal['strength']
            else:
                short_score += funding_signal['strength']
        
        # Generate signal if enough confirmations
        min_confirmations = 3
        min_score = 0.6
        
        if len(confirmations) >= min_confirmations:
            if long_score > min_score and long_score > short_score:
                return self._create_entry_signal('long', long_score, confirmations, market_data)
            elif short_score > min_score and short_score > long_score:
                return self._create_entry_signal('short', short_score, confirmations, market_data)
        
        return None
    
    def _check_rsi_signal(self, indicators: Dict) -> Dict:
        """Check RSI for signals."""
        rsi = indicators.get('rsi_14', 50)
        
        if rsi < Config.RSI_EXTREME_OVERSOLD:
            return {
                'type': 'rsi',
                'direction': 'bullish',
                'strength': 0.3,
                'description': f'RSI extreme oversold ({rsi:.1f})'
            }
        elif rsi < Config.RSI_OVERSOLD:
            return {
                'type': 'rsi',
                'direction': 'bullish',
                'strength': 0.2,
                'description': f'RSI oversold ({rsi:.1f})'
            }
        elif rsi > Config.RSI_EXTREME_OVERBOUGHT:
            return {
                'type': 'rsi',
                'direction': 'bearish',
                'strength': 0.3,
                'description': f'RSI extreme overbought ({rsi:.1f})'
            }
        elif rsi > Config.RSI_OVERBOUGHT:
            return {
                'type': 'rsi',
                'direction': 'bearish',
                'strength': 0.2,
                'description': f'RSI overbought ({rsi:.1f})'
            }
        
        return None
    
    def _check_ema_crossover(self, indicators: Dict) -> Dict:
        """Check EMA crossover signals."""
        crossover = indicators.get('ema_crossover')
        
        if crossover == 'bullish':
            return {
                'type': 'ema_crossover',
                'direction': 'bullish',
                'strength': 0.25,
                'description': 'EMA 9/21 bullish crossover'
            }
        elif crossover == 'bearish':
            return {
                'type': 'ema_crossover',
                'direction': 'bearish',
                'strength': 0.25,
                'description': 'EMA 9/21 bearish crossover'
            }
        
        return None
    
    def _check_bollinger_bands(self, indicators: Dict) -> Dict:
        """Check Bollinger Bands signals."""
        bb_squeeze = indicators.get('bb_squeeze')
        bb_position = indicators.get('bb_position')
        
        if bb_squeeze and indicators.get('bb_squeeze_direction'):
            return {
                'type': 'bb_squeeze',
                'direction': indicators['bb_squeeze_direction'],
                'strength': 0.3,
                'description': f'Bollinger Band squeeze {indicators["bb_squeeze_direction"]}'
            }
        elif bb_position == 'below':
            return {
                'type': 'bb_position',
                'direction': 'bullish',
                'strength': 0.2,
                'description': 'Price below lower Bollinger Band'
            }
        elif bb_position == 'above':
            return {
                'type': 'bb_position',
                'direction': 'bearish',
                'strength': 0.2,
                'description': 'Price above upper Bollinger Band'
            }
        
        return None
    
    def _check_macd(self, indicators: Dict) -> Dict:
        """Check MACD signals."""
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        macd_divergence = indicators.get('macd_divergence')
        
        # Check for crossover
        if macd > macd_signal and indicators.get('macd_histogram', 0) > 0:
            signal = {
                'type': 'macd_crossover',
                'direction': 'bullish',
                'strength': 0.2,
                'description': 'MACD bullish crossover'
            }
        elif macd < macd_signal and indicators.get('macd_histogram', 0) < 0:
            signal = {
                'type': 'macd_crossover',
                'direction': 'bearish',
                'strength': 0.2,
                'description': 'MACD bearish crossover'
            }
        else:
            signal = None
        
        # Check for divergence (stronger signal)
        if macd_divergence == 'bullish':
            return {
                'type': 'macd_divergence',
                'direction': 'bullish',
                'strength': 0.35,
                'description': 'MACD bullish divergence'
            }
        elif macd_divergence == 'bearish':
            return {
                'type': 'macd_divergence',
                'direction': 'bearish',
                'strength': 0.35,
                'description': 'MACD bearish divergence'
            }
        
        return signal
    
    def _check_patterns(self, indicators: Dict) -> Dict:
        """Check candlestick patterns."""
        # Check engulfing pattern
        if indicators.get('pattern_engulfing') == 'bullish':
            return {
                'type': 'pattern',
                'direction': 'bullish',
                'strength': 0.3,
                'description': 'Bullish engulfing pattern'
            }
        elif indicators.get('pattern_engulfing') == 'bearish':
            return {