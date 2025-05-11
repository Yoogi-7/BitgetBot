# src/simple_indicators.py
import pandas as pd
import numpy as np
import ta
from typing import Dict
from config.settings import Config


class SimpleIndicators:
    """Simplified technical indicators for basic trading."""
    
    def __init__(self):
        self.indicators = {}
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate basic technical indicators."""
        self.indicators = {}
        
        # Basic indicators
        self.calculate_moving_averages(df)
        self.calculate_rsi(df)
        self.calculate_volume_indicators(df)
        self.calculate_atr(df)
        
        # Simple trend detection
        self.calculate_trend(df)
        
        return self.indicators
    
    def calculate_moving_averages(self, df: pd.DataFrame):
        """Calculate EMAs."""
        self.indicators['ema_9'] = df['close'].ewm(span=9).mean().iloc[-1]
        self.indicators['ema_21'] = df['close'].ewm(span=21).mean().iloc[-1]
        
        # Basic trend
        if self.indicators['ema_9'] > self.indicators['ema_21']:
            self.indicators['ema_trend'] = 'bullish'
        else:
            self.indicators['ema_trend'] = 'bearish'
    
    def calculate_rsi(self, df: pd.DataFrame):
        """Calculate RSI."""
        for period in [5, 14]:
            rsi_value = ta.momentum.RSIIndicator(
                close=df['close'], 
                window=period
            ).rsi().iloc[-1]
            
            self.indicators[f'rsi_{period}'] = rsi_value
    
    def calculate_volume_indicators(self, df: pd.DataFrame):
        """Calculate volume indicators."""
        # Volume ratio
        volume_sma = df['volume'].rolling(window=20).mean()
        self.indicators['volume_ratio'] = df['volume'].iloc[-1] / volume_sma.iloc[-1] if volume_sma.iloc[-1] > 0 else 1
        
        # Volume spike detection
        self.indicators['volume_spike'] = self.indicators['volume_ratio'] > Config.VOLUME_SPIKE_THRESHOLD
    
    def calculate_atr(self, df: pd.DataFrame):
        """Calculate ATR."""
        atr_indicator = ta.volatility.AverageTrueRange(
            high=df['high'], 
            low=df['low'], 
            close=df['close'], 
            window=14
        )
        self.indicators['atr'] = atr_indicator.average_true_range().iloc[-1]
        
        # ATR percentage
        self.indicators['atr_percent'] = self.indicators['atr'] / df['close'].iloc[-1] * 100
    
    def calculate_trend(self, df: pd.DataFrame):
        """Simple trend detection."""
        # Price change
        self.indicators['price_change'] = df['close'].pct_change().iloc[-1] * 100
        
        # Basic trend
        if self.indicators['ema_trend'] == 'bullish' and self.indicators['price_change'] > 0:
            self.indicators['trend'] = 'bullish'
        elif self.indicators['ema_trend'] == 'bearish' and self.indicators['price_change'] < 0:
            self.indicators['trend'] = 'bearish'
        else:
            self.indicators['trend'] = 'neutral'