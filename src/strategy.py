# src/strategy.py
import pandas as pd
import numpy as np
import ta
from typing import Dict, List
from datetime import datetime
from config.settings import Config


class TradingStrategy:
    """Enhanced trading strategy with all RSI periods and session times."""
    
    def __init__(self):
        self.indicators = {}
    
    def generate_signal(self, market_data: Dict, analysis: Dict, positions: List[Dict]) -> Dict:
        """Generate trading signal based on market data and analysis."""
        df = market_data['ohlcv']
        
        # Calculate all indicators
        self._calculate_indicators(df)
        
        # Add session and time features
        self._add_session_features(df)
        
        # Initialize signal
        signal = {
            'action': None,
            'side': None,
            'reason': '',
            'entry_price': df['close'].iloc[-1],
            'stop_loss': None,
            'take_profit': None,
            'confidence': 0.0,
            'indicators': self.indicators
        }
        
        # Check for exit signals first
        exit_signal = self._check_exit_conditions(positions, df, analysis)
        if exit_signal:
            return exit_signal
        
        # Check for entry signals
        entry_signal = self._check_entry_conditions(df, analysis, positions)
        if entry_signal:
            return entry_signal
        
        return signal
    
    def _calculate_indicators(self, df: pd.DataFrame):
        """Calculate all technical indicators."""
        # Calculate RSI for all specified periods
        for period in Config.RSI_PERIODS:
            self.indicators[f'rsi_{period}'] = ta.momentum.RSIIndicator(
                close=df['close'], 
                window=period
            ).rsi().iloc[-1]
        
        # EMA trend
        ema_fast = df['close'].ewm(span=Config.EMA_FAST).mean()
        ema_slow = df['close'].ewm(span=Config.EMA_SLOW).mean()
        
        self.indicators['ema_fast'] = ema_fast.iloc[-1]
        self.indicators['ema_slow'] = ema_slow.iloc[-1]
        
        # Trend direction
        if ema_fast.iloc[-1] > ema_slow.iloc[-1]:
            self.indicators['trend'] = 'bullish'
        elif ema_fast.iloc[-1] < ema_slow.iloc[-1]:
            self.indicators['trend'] = 'bearish'
        else:
            self.indicators['trend'] = 'neutral'
        
        # VWAP
        vwap = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        self.indicators['vwap'] = vwap.iloc[-1]
        
        # ATR for different periods
        self.indicators['atr'] = ta.volatility.AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'], 
            window=Config.ATR_PERIOD
        ).average_true_range().iloc[-1]
        
        self.indicators['atr_short'] = ta.volatility.AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'], 
            window=Config.ATR_PERIOD_SHORT
        ).average_true_range().iloc[-1]
        
        # Volume analysis
        volume_sma = df['volume'].rolling(window=20).mean()
        self.indicators['volume_ratio'] = df['volume'].iloc[-1] / volume_sma.iloc[-1]
        self.indicators['volume_spike'] = self.indicators['volume_ratio'] > Config.VOLUME_SPIKE_THRESHOLD
        
        # Volume spike detection (500% in 1 minute)
        if len(df) > 1:
            volume_change = df['volume'].iloc[-1] / df['volume'].iloc[-2]
            self.indicators['volume_spike_500'] = volume_change > 5.0
        else:
            self.indicators['volume_spike_500'] = False
        
        # Price action
        self.indicators['price_change'] = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
    
    def _add_session_features(self, df: pd.DataFrame):
        """Add trading session features."""
        # Get current hour in UTC
        current_time = datetime.utcnow()
        hour_utc = current_time.hour
        
        # Check sessions
        self.indicators['session_asia'] = Config.ASIAN_SESSION[0] <= hour_utc < Config.ASIAN_SESSION[1]
        self.indicators['session_europe'] = Config.EUROPEAN_SESSION[0] <= hour_utc < Config.EUROPEAN_SESSION[1]
        self.indicators['session_us'] = Config.US_SESSION[0] <= hour_utc < Config.US_SESSION[1]
        
        # Check high liquidity hours
        self.indicators['high_liquidity'] = Config.HIGH_LIQUIDITY_HOURS[0] <= hour_utc < Config.HIGH_LIQUIDITY_HOURS[1]
        
        # Session overlaps
        self.indicators['session_overlap'] = (
            (self.indicators['session_europe'] and self.indicators['session_us']) or
            (self.indicators['session_asia'] and self.indicators['session_europe'])
        )
        
        # Current session name
        if self.indicators['session_asia']:
            self.indicators['current_session'] = 'Asia'
        elif self.indicators['session_europe']:
            self.indicators['current_session'] = 'Europe'
        elif self.indicators['session_us']:
            self.indicators['current_session'] = 'US'
        else:
            self.indicators['current_session'] = 'Other'
    
    def _check_entry_conditions(self, df: pd.DataFrame, analysis: Dict, positions: List[Dict]) -> Dict:
        """Check for entry conditions with enhanced scalping logic."""
        # Skip if max positions reached
        if len(positions) >= Config.MAX_OPEN_POSITIONS:
            return None
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Long conditions
        long_score = 0.0
        long_reasons = []
        
        # Check RSI oversold conditions on multiple timeframes
        rsi_5 = self.indicators.get('rsi_5', 50)
        rsi_7 = self.indicators.get('rsi_7', 50)
        
        if rsi_5 < 25 or rsi_7 < 27:
            long_score += 0.3
            long_reasons.append(f'RSI oversold (5:{rsi_5:.1f}, 7:{rsi_7:.1f})')
        
        # Price bounce from VWAP
        if last['close'] < self.indicators['vwap'] and last['close'] > prev['close']:
            long_score += 0.25
            long_reasons.append('VWAP bounce')
        
        # Volume spike with price increase
        if self.indicators.get('volume_spike_500', False) and self.indicators['price_change'] > 0:
            long_score += 0.35
            long_reasons.append('Volume spike 500% buy')
        
        # High liquidity hours bonus
        if self.indicators.get('high_liquidity', False):
            long_score += 0.1
            long_reasons.append('High liquidity hours')
        
        # Order book imbalance (buy pressure)
        if analysis.get('order_book_imbalance', 0) > Config.ORDER_BOOK_IMBALANCE_THRESHOLD:
            long_score += 0.3
            long_reasons.append('Buy pressure')
        
        # Short conditions
        short_score = 0.0
        short_reasons = []
        
        # Check RSI overbought conditions
        if rsi_5 > 75 or rsi_7 > 73:
            short_score += 0.3
            short_reasons.append(f'RSI overbought (5:{rsi_5:.1f}, 7:{rsi_7:.1f})')
        
        # Price rejection from VWAP
        if last['close'] > self.indicators['vwap'] and last['close'] < prev['close']:
            short_score += 0.25
            short_reasons.append('VWAP rejection')
        
        # Volume spike with price decrease
        if self.indicators.get('volume_spike_500', False) and self.indicators['price_change'] < 0:
            short_score += 0.35
            short_reasons.append('Volume spike 500% sell')
        
        # High liquidity hours bonus
        if self.indicators.get('high_liquidity', False):
            short_score += 0.1
            short_reasons.append('High liquidity hours')
        
        # Order book imbalance (sell pressure)
        if analysis.get('order_book_imbalance', 0) < -Config.ORDER_BOOK_IMBALANCE_THRESHOLD:
            short_score += 0.3
            short_reasons.append('Sell pressure')
        
        # Generate signal
        if long_score >= 0.7 and self.indicators['trend'] != 'bearish':
            return self._create_entry_signal('long', long_score, long_reasons, last, analysis)
        elif short_score >= 0.7 and self.indicators['trend'] != 'bullish':
            return self._create_entry_signal('short', short_score, short_reasons, last, analysis)
        
        return None
    
    def _check_exit_conditions(self, positions: List[Dict], df: pd.DataFrame, analysis: Dict) -> Dict:
        """Check for exit conditions."""
        if not positions:
            return None
        
        for position in positions:
            exit_conditions = []
            
            if position['side'] == 'long':
                # RSI extreme overbought
                if self.indicators.get('rsi_5', 50) > 70:
                    exit_conditions.append('RSI_5 overbought')
                
                # Price above VWAP target
                if df['close'].iloc[-1] > self.indicators['vwap'] * 1.005:
                    exit_conditions.append('VWAP target reached')
                
                # Volume exhaustion
                if self.indicators.get('volume_spike_500', False) and df['volume'].iloc[-1] < df['volume'].iloc[-2]:
                    exit_conditions.append('Volume exhaustion')
            
            elif position['side'] == 'short':
                # RSI extreme oversold
                if self.indicators.get('rsi_5', 50) < 30:
                    exit_conditions.append('RSI_5 oversold')
                
                # Price below VWAP target
                if df['close'].iloc[-1] < self.indicators['vwap'] * 0.995:
                    exit_conditions.append('VWAP target reached')
                
                # Volume exhaustion
                if self.indicators.get('volume_spike_500', False) and df['volume'].iloc[-1] < df['volume'].iloc[-2]:
                    exit_conditions.append('Volume exhaustion')
            
            if exit_conditions:
                return {
                    'action': 'CLOSE',
                    'side': position['side'],
                    'reason': 'Exit: ' + ', '.join(exit_conditions),
                    'entry_price': df['close'].iloc[-1],
                    'confidence': 0.9,
                    'indicators': self.indicators
                }
        
        return None
    
    def _create_entry_signal(self, side: str, confidence: float, reasons: List[str], 
                           last: pd.Series, analysis: Dict) -> Dict:
        """Create entry signal with proper risk management."""
        # Get spread from analysis
        spread = analysis.get('spread', 0.001)  # Default 0.1% if not available
        
        # Use short-term ATR for stops
        atr = self.indicators.get('atr_short', self.indicators.get('atr', last['close'] * 0.02))
        
        # Calculate stop loss based on spread and ATR
        spread_based_stop = spread * Config.SPREAD_MULTIPLIER
        atr_based_stop = atr * 1.5
        stop_distance = max(spread_based_stop, atr_based_stop)
        
        if side == 'long':
            stop_loss = last['close'] * (1 - stop_distance)
            take_profit = last['close'] * (1 + (stop_distance * 2))
        else:
            stop_loss = last['close'] * (1 + stop_distance)
            take_profit = last['close'] * (1 - (stop_distance * 2))
        
        return {
            'action': 'OPEN',
            'side': side,
            'reason': f"Scalp {side}: {', '.join(reasons)}",
            'entry_price': last['close'],
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': confidence,
            'indicators': self.indicators,
            'atr': atr,
            'spread': spread
        }