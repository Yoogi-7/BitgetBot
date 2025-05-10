# src/strategies.py
import pandas as pd
import ta
from config.settings import Config
import logging
import numpy as np

class FuturesStrategy:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_indicators(self, df):
        """Oblicza wskaźniki techniczne"""
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=Config.RSI_PERIOD).rsi()
        
        # EMA (Exponential Moving Average)
        df['ema_fast'] = ta.trend.EMAIndicator(close=df['close'], window=Config.EMA_FAST).ema_indicator()
        df['ema_slow'] = ta.trend.EMAIndicator(close=df['close'], window=Config.EMA_SLOW).ema_indicator()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_lower'] = bollinger.bollinger_lband()
        df['bb_middle'] = bollinger.bollinger_mavg()
        
        # ATR (Average True Range) - do stop loss
        df['atr'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close']).average_true_range()
        
        # Volume SMA
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        # MACD
        macd = ta.trend.MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        return df
    
    def check_trend(self, df):
        """Sprawdza kierunek trendu"""
        last = df.iloc[-1]
        
        # Trend wzrostowy
        if last['ema_fast'] > last['ema_slow'] and last['close'] > last['ema_fast']:
            return 'bullish'
        # Trend spadkowy
        elif last['ema_fast'] < last['ema_slow'] and last['close'] < last['ema_fast']:
            return 'bearish'
        else:
            return 'neutral'
    
    def generate_signal(self, df, existing_positions=[]):
        """Generuje sygnały tradingowe"""
        if df is None or len(df) < 50:
            return {'action': None, 'reason': 'Insufficient data'}
        
        df = self.calculate_indicators(df)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = {
            'action': None,
            'side': None,  # 'long' lub 'short'
            'reason': '',
            'entry_price': last['close'],
            'stop_loss': None,
            'take_profit': None,
            'confidence': 0,
            'indicators': {
                'rsi': last['rsi'],
                'ema_fast': last['ema_fast'],
                'ema_slow': last['ema_slow'],
                'trend': self.check_trend(df),
                'volume_ratio': last['volume'] / last['volume_sma'] if last['volume_sma'] > 0 else 1
            }
        }
        
        # Sprawdź czy wolumen jest wystarczający
        if last['volume'] < last['volume_sma'] * Config.MIN_VOLUME_MULTIPLIER:
            signal['reason'] = 'Low volume'
            return signal
        
        trend = self.check_trend(df)
        
        # === LONG SIGNALS ===
        if trend == 'bullish':
            # RSI Oversold Bounce
            if last['rsi'] < Config.RSI_OVERSOLD and prev['rsi'] >= Config.RSI_OVERSOLD:
                signal['action'] = 'OPEN'
                signal['side'] = 'long'
                signal['reason'] = 'RSI oversold bounce in uptrend'
                signal['confidence'] = 0.8
                signal['stop_loss'] = last['close'] - (last['atr'] * 1.5)
                signal['take_profit'] = last['close'] + (last['atr'] * 2)
            
            # Bollinger Band Bounce
            elif last['low'] <= last['bb_lower'] and last['close'] > last['bb_lower']:
                signal['action'] = 'OPEN'
                signal['side'] = 'long'
                signal['reason'] = 'Bollinger bounce in uptrend'
                signal['confidence'] = 0.7
                signal['stop_loss'] = last['bb_lower'] - (last['atr'] * 0.5)
                signal['take_profit'] = last['bb_middle']
        
        # === SHORT SIGNALS ===
        elif trend == 'bearish':
            # RSI Overbought Reversal
            if last['rsi'] > Config.RSI_OVERBOUGHT and prev['rsi'] <= Config.RSI_OVERBOUGHT:
                signal['action'] = 'OPEN'
                signal['side'] = 'short'
                signal['reason'] = 'RSI overbought reversal in downtrend'
                signal['confidence'] = 0.8
                signal['stop_loss'] = last['close'] + (last['atr'] * 1.5)
                signal['take_profit'] = last['close'] - (last['atr'] * 2)
            
            # Bollinger Band Rejection
            elif last['high'] >= last['bb_upper'] and last['close'] < last['bb_upper']:
                signal['action'] = 'OPEN'
                signal['side'] = 'short'
                signal['reason'] = 'Bollinger rejection in downtrend'
                signal['confidence'] = 0.7
                signal['stop_loss'] = last['bb_upper'] + (last['atr'] * 0.5)
                signal['take_profit'] = last['bb_middle']
        
        # === EXIT SIGNALS (dla istniejących pozycji) ===
        for position in existing_positions:
            if position['side'] == 'long':
                # Exit long jeśli RSI overbought lub trend się zmienia
                if last['rsi'] > Config.RSI_OVERBOUGHT or trend == 'bearish':
                    signal['action'] = 'CLOSE'
                    signal['side'] = 'long'
                    signal['reason'] = 'Exit long - overbought or trend change'
                    signal['confidence'] = 0.9
            
            elif position['side'] == 'short':
                # Exit short jeśli RSI oversold lub trend się zmienia
                if last['rsi'] < Config.RSI_OVERSOLD or trend == 'bullish':
                    signal['action'] = 'CLOSE'
                    signal['side'] = 'short'
                    signal['reason'] = 'Exit short - oversold or trend change'
                    signal['confidence'] = 0.9
        
        return signal
    
    def calculate_position_size(self, account_balance, entry_price, stop_loss_price):
        """Oblicza wielkość pozycji na podstawie ryzyka"""
        risk_amount = account_balance * 0.01  # 1% ryzyka na trade
        price_difference = abs(entry_price - stop_loss_price)
        position_size = risk_amount / price_difference
        
        # Ogranicz do maksymalnej wielkości
        max_position = Config.MAX_POSITION_SIZE / entry_price
        return min(position_size, max_position)