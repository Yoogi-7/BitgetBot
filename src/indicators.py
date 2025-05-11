# src/indicators.py
import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Optional, Tuple
from config.settings import Config


class TechnicalIndicators:
    """Comprehensive technical indicators calculation."""
    
    def __init__(self):
        self.indicators = {}
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate all technical indicators."""
        self.indicators = {}
        
        # Price action indicators
        self.calculate_moving_averages(df)
        self.calculate_bollinger_bands(df)
        self.calculate_macd(df)
        self.calculate_rsi(df)
        
        # Volume indicators
        self.calculate_volume_indicators(df)
        
        # Volatility indicators
        self.calculate_atr(df)
        
        # Pattern detection
        self.detect_candlestick_patterns(df)
        
        return self.indicators
    
    def calculate_moving_averages(self, df: pd.DataFrame):
        """Calculate EMA and SMA indicators."""
        # EMAs
        self.indicators['ema_5'] = df['close'].ewm(span=Config.EMA_VERY_SHORT).mean().iloc[-1]
        self.indicators['ema_9'] = df['close'].ewm(span=Config.EMA_SHORT).mean().iloc[-1]
        self.indicators['ema_21'] = df['close'].ewm(span=Config.EMA_LONG).mean().iloc[-1]
        self.indicators['ema_50'] = df['close'].ewm(span=Config.EMA_TREND).mean().iloc[-1]
        
        # SMAs
        for period in Config.SMA_PERIODS:
            self.indicators[f'sma_{period}'] = df['close'].rolling(window=period).mean().iloc[-1]
        
        # EMA Crossovers
        ema_short = df['close'].ewm(span=Config.EMA_SHORT).mean()
        ema_long = df['close'].ewm(span=Config.EMA_LONG).mean()
        
        # Check for crossover
        if len(df) >= 2:
            current_diff = ema_short.iloc[-1] - ema_long.iloc[-1]
            prev_diff = ema_short.iloc[-2] - ema_long.iloc[-2]
            
            if current_diff > 0 and prev_diff <= 0:
                self.indicators['ema_crossover'] = 'bullish'
            elif current_diff < 0 and prev_diff >= 0:
                self.indicators['ema_crossover'] = 'bearish'
            else:
                self.indicators['ema_crossover'] = 'none'
        
        # Trend strength
        ema_9 = self.indicators['ema_9']
        ema_21 = self.indicators['ema_21']
        ema_50 = self.indicators['ema_50']
        
        if ema_9 > ema_21 > ema_50:
            self.indicators['trend'] = 'strong_bullish'
        elif ema_9 < ema_21 < ema_50:
            self.indicators['trend'] = 'strong_bearish'
        elif ema_9 > ema_21:
            self.indicators['trend'] = 'bullish'
        elif ema_9 < ema_21:
            self.indicators['trend'] = 'bearish'
        else:
            self.indicators['trend'] = 'neutral'
    
    def calculate_bollinger_bands(self, df: pd.DataFrame):
        """Calculate Bollinger Bands and detect squeeze."""
        bb_indicator = ta.volatility.BollingerBands(
            close=df['close'],
            window=Config.BB_PERIOD,
            window_dev=Config.BB_STD
        )
        
        self.indicators['bb_upper'] = bb_indicator.bollinger_hband().iloc[-1]
        self.indicators['bb_middle'] = bb_indicator.bollinger_mavg().iloc[-1]
        self.indicators['bb_lower'] = bb_indicator.bollinger_lband().iloc[-1]
        
        # Bollinger Band width
        bb_width = (self.indicators['bb_upper'] - self.indicators['bb_lower']) / self.indicators['bb_middle']
        self.indicators['bb_width'] = bb_width
        
        # Detect Bollinger Band squeeze
        if bb_width < Config.BB_SQUEEZE_THRESHOLD:
            self.indicators['bb_squeeze'] = True
            
            # Determine squeeze direction
            current_price = df['close'].iloc[-1]
            if current_price > self.indicators['bb_middle']:
                self.indicators['bb_squeeze_direction'] = 'bullish'
            else:
                self.indicators['bb_squeeze_direction'] = 'bearish'
        else:
            self.indicators['bb_squeeze'] = False
            self.indicators['bb_squeeze_direction'] = 'none'
        
        # Price position relative to bands
        if current_price > self.indicators['bb_upper']:
            self.indicators['bb_position'] = 'above'
        elif current_price < self.indicators['bb_lower']:
            self.indicators['bb_position'] = 'below'
        else:
            self.indicators['bb_position'] = 'inside'
    
    def calculate_macd(self, df: pd.DataFrame):
        """Calculate MACD and detect divergences."""
        macd_indicator = ta.trend.MACD(
            close=df['close'],
            window_slow=Config.MACD_SLOW,
            window_fast=Config.MACD_FAST,
            window_sign=Config.MACD_SIGNAL
        )
        
        self.indicators['macd'] = macd_indicator.macd().iloc[-1]
        self.indicators['macd_signal'] = macd_indicator.macd_signal().iloc[-1]
        self.indicators['macd_histogram'] = macd_indicator.macd_diff().iloc[-1]
        
        # MACD divergence detection
        if len(df) >= 20:
            self._detect_macd_divergence(df, macd_indicator)
    
    def _detect_macd_divergence(self, df: pd.DataFrame, macd_indicator):
        """Detect MACD divergences."""
        macd_line = macd_indicator.macd()
        prices = df['close']
        
        # Look for divergences in last 20 bars
        lookback = 20
        if len(df) < lookback:
            return
        
        # Find local extremes
        price_highs = []
        price_lows = []
        macd_highs = []
        macd_lows = []
        
        for i in range(-lookback, -1):
            # Local high
            if prices.iloc[i] > prices.iloc[i-1] and prices.iloc[i] > prices.iloc[i+1]:
                price_highs.append((i, prices.iloc[i]))
                macd_highs.append((i, macd_line.iloc[i]))
            
            # Local low
            if prices.iloc[i] < prices.iloc[i-1] and prices.iloc[i] < prices.iloc[i+1]:
                price_lows.append((i, prices.iloc[i]))
                macd_lows.append((i, macd_line.iloc[i]))
        
        # Check for bearish divergence (price higher high, MACD lower high)
        if len(price_highs) >= 2 and len(macd_highs) >= 2:
            if price_highs[-1][1] > price_highs[-2][1] and macd_highs[-1][1] < macd_highs[-2][1]:
                self.indicators['macd_divergence'] = 'bearish'
                return
        
        # Check for bullish divergence (price lower low, MACD higher low)
        if len(price_lows) >= 2 and len(macd_lows) >= 2:
            if price_lows[-1][1] < price_lows[-2][1] and macd_lows[-1][1] > macd_lows[-2][1]:
                self.indicators['macd_divergence'] = 'bullish'
                return
        
        self.indicators['macd_divergence'] = 'none'
    
    def calculate_rsi(self, df: pd.DataFrame):
        """Calculate RSI for multiple periods and detect conditions."""
        for period in Config.RSI_PERIODS:
            rsi_value = ta.momentum.RSIIndicator(
                close=df['close'], 
                window=period
            ).rsi().iloc[-1]
            
            self.indicators[f'rsi_{period}'] = rsi_value
            
            # RSI conditions for RSI 14
            if period == 14:
                if rsi_value < Config.RSI_EXTREME_OVERSOLD:
                    self.indicators['rsi_condition'] = 'extreme_oversold'
                elif rsi_value < Config.RSI_OVERSOLD:
                    self.indicators['rsi_condition'] = 'oversold'
                elif rsi_value > Config.RSI_EXTREME_OVERBOUGHT:
                    self.indicators['rsi_condition'] = 'extreme_overbought'
                elif rsi_value > Config.RSI_OVERBOUGHT:
                    self.indicators['rsi_condition'] = 'overbought'
                else:
                    self.indicators['rsi_condition'] = 'neutral'
    
    def calculate_volume_indicators(self, df: pd.DataFrame):
        """Calculate volume-based indicators."""
        # Volume analysis
        volume_sma = df['volume'].rolling(window=20).mean()
        self.indicators['volume_ratio'] = df['volume'].iloc[-1] / volume_sma.iloc[-1]
        self.indicators['volume_sma_20'] = volume_sma.iloc[-1]
        
        # Volume spike detection
        self.indicators['volume_spike'] = self.indicators['volume_ratio'] > Config.VOLUME_SPIKE_THRESHOLD
        self.indicators['volume_spike_extreme'] = self.indicators['volume_ratio'] > Config.VOLUME_SPIKE_EXTREME
        
        # Volume trend
        volume_ema_short = df['volume'].ewm(span=5).mean()
        volume_ema_long = df['volume'].ewm(span=20).mean()
        
        if volume_ema_short.iloc[-1] > volume_ema_long.iloc[-1]:
            self.indicators['volume_trend'] = 'increasing'
        else:
            self.indicators['volume_trend'] = 'decreasing'
    
    def calculate_atr(self, df: pd.DataFrame):
        """Calculate ATR for different periods."""
        # Standard ATR
        atr_indicator = ta.volatility.AverageTrueRange(
            high=df['high'], 
            low=df['low'], 
            close=df['close'], 
            window=14
        )
        self.indicators['atr'] = atr_indicator.average_true_range().iloc[-1]
        
        # Short-term ATR
        atr_short = ta.volatility.AverageTrueRange(
            high=df['high'], 
            low=df['low'], 
            close=df['close'], 
            window=5
        )
        self.indicators['atr_short'] = atr_short.average_true_range().iloc[-1]
        
        # ATR percentage
        self.indicators['atr_percent'] = self.indicators['atr'] / df['close'].iloc[-1] * 100
    
    def detect_candlestick_patterns(self, df: pd.DataFrame):
        """Detect candlestick patterns."""
        if len(df) < 5:
            return
        
        # Current and previous candles
        current = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]
        
        # Engulfing patterns
        self._detect_engulfing(current, prev)
        
        # Pin bar / Hammer / Shooting star
        self._detect_pin_bar(current, prev)
        
        # Breakout patterns
        self._detect_breakout(df)
        
        # Low/High trap patterns
        self._detect_traps(df)
    
    def _detect_engulfing(self, current: pd.Series, prev: pd.Series):
        """Detect engulfing patterns."""
        # Bullish engulfing
        if (prev['close'] < prev['open'] and  # Previous bearish
            current['close'] > current['open'] and  # Current bullish
            current['open'] < prev['close'] and  # Opens below prev close
            current['close'] > prev['open']):  # Closes above prev open
            self.indicators['pattern_engulfing'] = 'bullish'
        
        # Bearish engulfing
        elif (prev['close'] > prev['open'] and  # Previous bullish
              current['close'] < current['open'] and  # Current bearish
              current['open'] > prev['close'] and  # Opens above prev close
              current['close'] < prev['open']):  # Closes below prev open
            self.indicators['pattern_engulfing'] = 'bearish'
        else:
            self.indicators['pattern_engulfing'] = 'none'
    
    def _detect_pin_bar(self, current: pd.Series, prev: pd.Series):
        """Detect pin bar patterns."""
        body_size = abs(current['close'] - current['open'])
        upper_wick = current['high'] - max(current['close'], current['open'])
        lower_wick = min(current['close'], current['open']) - current['low']
        total_range = current['high'] - current['low']
        
        if total_range == 0:
            return
        
        # Pin bar criteria: small body, long wick
        if body_size / total_range < 0.3:  # Body less than 30% of range
            if lower_wick / total_range > 0.6:  # Lower wick > 60%
                self.indicators['pattern_pin_bar'] = 'bullish'
            elif upper_wick / total_range > 0.6:  # Upper wick > 60%
                self.indicators['pattern_pin_bar'] = 'bearish'
            else:
                self.indicators['pattern_pin_bar'] = 'none'
        else:
            self.indicators['pattern_pin_bar'] = 'none'
    
    def _detect_breakout(self, df: pd.DataFrame):
        """Detect breakout patterns."""
        lookback = 20
        if len(df) < lookback:
            return
        
        current_price = df['close'].iloc[-1]
        recent_high = df['high'].iloc[-lookback:-1].max()
        recent_low = df['low'].iloc[-lookback:-1].min()
        
        # Breakout detection
        if current_price > recent_high:
            self.indicators['pattern_breakout'] = 'bullish'
        elif current_price < recent_low:
            self.indicators['pattern_breakout'] = 'bearish'
        else:
            self.indicators['pattern_breakout'] = 'none'
        
        # Resistance/Support levels
        self.indicators['resistance'] = recent_high
        self.indicators['support'] = recent_low
    
    def _detect_traps(self, df: pd.DataFrame):
        """Detect low/high trap patterns."""
        if len(df) < 10:
            return
        
        # Low trap: false breakdown followed by recovery
        recent_low = df['low'].iloc[-10:-2].min()
        if (df['low'].iloc[-2] < recent_low and  # Break below recent low
            df['close'].iloc[-1] > recent_low):  # Close back above
            self.indicators['pattern_trap'] = 'low_trap'
        
        # High trap: false breakout followed by reversal
        recent_high = df['high'].iloc[-10:-2].max()
        if (df['high'].iloc[-2] > recent_high and  # Break above recent high
            df['close'].iloc[-1] < recent_high):  # Close back below
            self.indicators['pattern_trap'] = 'high_trap'
        else:
            self.indicators['pattern_trap'] = 'none'