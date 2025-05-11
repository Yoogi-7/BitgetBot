# src/strategy.py
import pandas as pd
import numpy as np
import ta
from typing import Dict, List
from config.settings import Config


class TradingStrategy:
    """Simplified trading strategy focused on scalping."""
    
    def __init__(self):
        self.indicators = {}
    
    def generate_signal(self, market_data: Dict, analysis: Dict, positions: List[Dict]) -> Dict:
        """Generate trading signal based on market data and analysis."""
        df = market_data['ohlcv']
        
        # Calculate indicators
        self._calculate_indicators(df)
        
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
        """Calculate technical indicators."""
        # RSI
        self.indicators['rsi'] = ta.momentum.RSIIndicator(
            close=df['close'], 
            window=Config.RSI_PERIOD
        ).rsi().iloc[-1]
        
        # RSI for scalping
        self.indicators['rsi_5'] = ta.momentum.RSIIndicator(
            close=df['close'], 
            window=5
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
        
        # Volume analysis
        volume_sma = df['volume'].rolling(window=20).mean()
        self.indicators['volume_ratio'] = df['volume'].iloc[-1] / volume_sma.iloc[-1]
        self.indicators['volume_spike'] = self.indicators['volume_ratio'] > Config.VOLUME_SPIKE_THRESHOLD
        
        # Price action
        self.indicators['price_change'] = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
    
    def _check_entry_conditions(self, df: pd.DataFrame, analysis: Dict, positions: List[Dict]) -> Dict:
        """Check for entry conditions."""
        # Skip if max positions reached
        if len(positions) >= Config.MAX_OPEN_POSITIONS:
            return None
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Long conditions
        long_score = 0.0
        long_reasons = []
        
        # RSI oversold
        if self.indicators['rsi_5'] < Config.RSI_OVERSOLD:
            long_score += 0.3
            long_reasons.append('RSI oversold')
        
        # Price bounce from VWAP
        if last['close'] < self.indicators['vwap'] and last['close'] > prev['close']:
            long_score += 0.25
            long_reasons.append('VWAP bounce')
        
        # Volume spike with price increase
        if self.indicators['volume_spike'] and self.indicators['price_change'] > 0:
            long_score += 0.35
            long_reasons.append('Volume spike buy')
        
        # Order book imbalance (buy pressure)
        if analysis.get('order_book_imbalance', 0) > Config.ORDER_BOOK_IMBALANCE_THRESHOLD:
            long_score += 0.3
            long_reasons.append('Buy pressure')
        
        # Short conditions
        short_score = 0.0
        short_reasons = []
        
        # RSI overbought
        if self.indicators['rsi_5'] > Config.RSI_OVERBOUGHT:
            short_score += 0.3
            short_reasons.append('RSI overbought')
        
        # Price rejection from VWAP
        if last['close'] > self.indicators['vwap'] and last['close'] < prev['close']:
            short_score += 0.25
            short_reasons.append('VWAP rejection')
        
        # Volume spike with price decrease
        if self.indicators['volume_spike'] and self.indicators['price_change'] < 0:
            short_score += 0.35
            short_reasons.append('Volume spike sell')
        
        # Order book imbalance (sell pressure)
        if analysis.get('order_book_imbalance', 0) < -Config.ORDER_BOOK_IMBALANCE_THRESHOLD:
            short_score += 0.3
            short_reasons.append('Sell pressure')
        
        # Generate signal
        if long_score >= 0.7 and self.indicators['trend'] != 'bearish':
            return self._create_entry_signal('long', long_score, long_reasons, last)
        elif short_score >= 0.7 and self.indicators['trend'] != 'bullish':
            return self._create_entry_signal('short', short_score, short_reasons, last)
        
        return None
    
    def _check_exit_conditions(self, positions: List[Dict], df: pd.DataFrame, analysis: Dict) -> Dict:
        """Check for exit conditions."""
        if not positions:
            return None
        
        for position in positions:
            exit_conditions = []
            
            if position['side'] == 'long':
                # RSI extreme overbought
                if self.indicators['rsi_5'] > 70:
                    exit_conditions.append('RSI overbought')
                
                # Price above VWAP target
                if df['close'].iloc[-1] > self.indicators['vwap'] * 1.005:
                    exit_conditions.append('VWAP target reached')
                
                # Volume exhaustion
                if self.indicators['volume_spike'] and df['volume'].iloc[-1] < df['volume'].iloc[-2]:
                    exit_conditions.append('Volume exhaustion')
            
            elif position['side'] == 'short':
                # RSI extreme oversold
                if self.indicators['rsi_5'] < 30:
                    exit_conditions.append('RSI oversold')
                
                # Price below VWAP target
                if df['close'].iloc[-1] < self.indicators['vwap'] * 0.995:
                    exit_conditions.append('VWAP target reached')
                
                # Volume exhaustion
                if self.indicators['volume_spike'] and df['volume'].iloc[-1] < df['volume'].iloc[-2]:
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
    
    def _create_entry_signal(self, side: str, confidence: float, reasons: List[str], last: pd.Series) -> Dict:
        """Create entry signal with proper risk management."""
        # Calculate ATR for dynamic stops
        atr = ta.volatility.AverageTrueRange(
            high=last.name, 
            low=last.name, 
            close=last['close'], 
            window=5
        ).average_true_range().iloc[-1] if hasattr(last, 'name') else last['close'] * 0.02
        
        if side == 'long':
            stop_loss = last['close'] - (atr * 1.5)
            take_profit = last['close'] + (atr * 2.0)
        else:
            stop_loss = last['close'] + (atr * 1.5)
            take_profit = last['close'] - (atr * 2.0)
        
        return {
            'action': 'OPEN',
            'side': side,
            'reason': f"Scalp {side}: {', '.join(reasons)}",
            'entry_price': last['close'],
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': confidence,
            'indicators': self.indicators
        }