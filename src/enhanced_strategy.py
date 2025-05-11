# src/enhanced_strategy.py
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from config.settings import Config
from src.indicators import TechnicalIndicators


class EnhancedTradingStrategy:
    """Enhanced trading strategy with advanced pattern recognition and multi-level exit strategies."""
    
    def __init__(self):
        self.indicators_calculator = TechnicalIndicators()
        self.indicators = {}
        
        # Multi-level take profit settings
        self.TP1_LEVELS = {
            'scalping': 0.003,  # 0.3%
            'intraday': 0.005,  # 0.5%
            'swing': 0.01       # 1%
        }
        
        self.TP2_LEVELS = {
            'scalping': 0.006,  # 0.6%
            'intraday': 0.01,   # 1%
            'swing': 0.02       # 2%
        }
        
        # Exit proportion at TP1
        self.TP1_EXIT_RATIO = 0.5  # Exit 50% at TP1
        
        # Order settings
        self.LIMIT_BUFFER = 0.0002  # 0.02% buffer for limit orders
        self.BREAKOUT_CONFIRMATION_BARS = 2  # Bars needed to confirm breakout
        
        # Emergency exit thresholds
        self.VOLATILITY_SPIKE_THRESHOLD = 3.0  # 300% ATR increase
        self.RAPID_PRICE_CHANGE = 0.02  # 2% rapid price movement
        
        # Local extremes lookback
        self.LOCAL_EXTREMES_LOOKBACK = 10  # Bars to look for local highs/lows
        
        # Trailing stop settings
        self.TRAILING_STOP_ACTIVATION = 0.005  # 0.5% profit to activate trailing
        self.TRAILING_STOP_DISTANCE = 0.003    # 0.3% trailing distance
    
    def generate_signal(self, market_data: Dict, positions: List[Dict]) -> Dict:
        """Generate trading signal with enhanced analysis."""
        # Get OHLCV data from default timeframe
        timeframe_data = market_data.get('timeframes', {}).get(Config.DEFAULT_TIMEFRAME, {})
        df = timeframe_data.get('ohlcv')
        
        if df is None or df.empty:
            return self._empty_signal()
        
        # Calculate all indicators
        self.indicators = self.indicators_calculator.calculate_all_indicators(df)
        
        # Add additional data to indicators
        self._add_market_metrics(market_data)
        
        # Initialize signal
        signal = {
            'action': None,
            'side': None,
            'reason': '',
            'entry_price': df['close'].iloc[-1],
            'stop_loss': None,
            'take_profit': None,
            'tp1': None,
            'tp2': None,
            'confidence': 0.0,
            'indicators': self.indicators,
            'atr': self.indicators.get('atr', 0),
            'strategy_type': 'scalping'  # Default to scalping
        }
        
        # Check for exit signals first
        exit_signal = self._check_exit_conditions(positions, market_data)
        if exit_signal:
            return exit_signal
        
        # Check for entry signals
        entry_signal = self._check_entry_conditions(market_data, positions)
        if entry_signal:
            return entry_signal
        
        return signal
    
    def _add_market_metrics(self, market_data: Dict):
        """Add market metrics to indicators."""
        # Order book metrics
        order_book = market_data.get('order_book', {})
        if order_book:
            imbalance = order_book.get('imbalance', {})
            self.indicators['order_book_imbalance'] = imbalance.get('level_5', {}).get('imbalance', 0)
            self.indicators['spread'] = order_book.get('l1', {}).get('ask', 0) - order_book.get('l1', {}).get('bid', 0)
        
        # Funding rate
        funding = market_data.get('funding_rate', {})
        if funding:
            self.indicators['funding_rate'] = funding.get('current', 0)
            self.indicators['funding_extreme'] = abs(self.indicators['funding_rate']) > Config.FUNDING_RATE_THRESHOLD
        
        # Open interest
        oi = market_data.get('open_interest', {})
        if oi:
            self.indicators['oi_change'] = oi.get('change_percent_24h', 0)
            self.indicators['oi_increasing'] = self.indicators['oi_change'] > Config.OPEN_INTEREST_CHANGE_THRESHOLD
        
        # Multi-timeframe trend
        trends = []
        for tf, tf_data in market_data.get('timeframes', {}).items():
            tf_indicators = tf_data.get('indicators', {})
            if 'trend' in tf_indicators:
                trends.append(tf_indicators['trend'])
        
        if trends and all(t == trends[0] for t in trends):
            self.indicators['trend_aligned'] = True
            self.indicators['aligned_trend'] = trends[0]
        else:
            self.indicators['trend_aligned'] = False
    
    def _check_entry_conditions(self, market_data: Dict, positions: List[Dict]) -> Optional[Dict]:
        """Check for entry conditions with enhanced pattern recognition."""
        # Skip if max positions reached
        if len(positions) >= Config.MAX_OPEN_POSITIONS:
            return None
        
        # Get current price data
        timeframe_data = market_data.get('timeframes', {}).get(Config.DEFAULT_TIMEFRAME, {})
        df = timeframe_data.get('ohlcv')
        
        if df is None or df.empty:
            return None
        
        last = df.iloc[-1]
        
        # Initialize scores for long and short
        long_score, long_reasons = self._calculate_long_score(market_data)
        short_score, short_reasons = self._calculate_short_score(market_data)
        
        # Determine signal type
        if long_score >= 0.7:
            strategy_type = self._determine_strategy_type(market_data)
            return self._create_enhanced_entry_signal(
                'long', long_score, long_reasons, last, market_data, strategy_type
            )
        elif short_score >= 0.7:
            strategy_type = self._determine_strategy_type(market_data)
            return self._create_enhanced_entry_signal(
                'short', short_score, short_reasons, last, market_data, strategy_type
            )
        
        return None
    
    def _calculate_long_score(self, market_data: Dict) -> tuple:
        """Calculate score for long entry."""
        score = 0.0
        reasons = []
        
        # RSI conditions (multiple timeframes)
        rsi_5 = self.indicators.get('rsi_5', 50)
        rsi_14 = self.indicators.get('rsi_14', 50)
        
        if rsi_5 < 25:  # Extreme oversold on 5m
            score += 0.3
            reasons.append(f'RSI_5 extreme oversold ({rsi_5:.1f})')
        elif rsi_14 < 30:  # Standard oversold
            score += 0.2
            reasons.append(f'RSI_14 oversold ({rsi_14:.1f})')
        
        # Volume spike patterns
        if self.indicators.get('volume_spike_500'):  # 500% one-minute spike
            score += 0.35
            reasons.append('Volume spike 500% (1min)')
        elif self.indicators.get('volume_spike'):
            score += 0.2
            reasons.append('Volume spike')
        
        # MACD signals
        if self.indicators.get('macd_crossover') == 'bullish':
            score += 0.25
            reasons.append('MACD bullish crossover')
        if self.indicators.get('macd_divergence') == 'bullish':
            score += 0.3
            reasons.append('MACD bullish divergence')
        
        # EMA crossover
        if self.indicators.get('ema_crossover') == 'bullish':
            score += 0.25
            reasons.append('EMA 9/21 bullish crossover')
        
        # Bollinger Bands
        if self.indicators.get('bb_squeeze') and self.indicators.get('bb_squeeze_direction') == 'bullish':
            score += 0.3
            reasons.append('Bollinger Band squeeze breakout (bullish)')
        elif self.indicators.get('bb_position') == 'below':
            score += 0.2
            reasons.append('Price below lower Bollinger Band')
        
        # Order book imbalance
        imbalance = self.indicators.get('order_book_imbalance', 0)
        if imbalance > 0.3:
            score += 0.2
            reasons.append(f'Strong buy pressure ({imbalance:.2f})')
        
        # Candlestick patterns
        if self.indicators.get('pattern_engulfing') == 'bullish':
            score += 0.2
            reasons.append('Bullish engulfing pattern')
        
        if self.indicators.get('pattern_pin_bar') == 'bullish':
            score += 0.15
            reasons.append('Bullish pin bar')
        
        if self.indicators.get('pattern_breakout') == 'bullish':
            score += 0.25
            reasons.append('Bullish breakout')
        
        if self.indicators.get('pattern_trap') == 'low_trap':
            score += 0.2
            reasons.append('Low trap (false breakdown)')
        
        # Trend alignment bonus
        if self.indicators.get('trend_aligned') and self.indicators.get('aligned_trend') == 'bullish':
            score += 0.15
            reasons.append('Multi-timeframe bullish trend')
        
        # VWAP position
        if self.indicators.get('vwap'):
            current_price = market_data.get('ticker', {}).get('last', 0)
            vwap = self.indicators.get('vwap')
            if current_price < vwap * 0.995:  # Price below VWAP
                score += 0.15
                reasons.append('Price below VWAP')
        
        return score, reasons
    
    def _calculate_short_score(self, market_data: Dict) -> tuple:
        """Calculate score for short entry."""
        score = 0.0
        reasons = []
        
        # RSI conditions
        rsi_5 = self.indicators.get('rsi_5', 50)
        rsi_14 = self.indicators.get('rsi_14', 50)
        
        if rsi_5 > 75:  # Extreme overbought on 5m
            score += 0.3
            reasons.append(f'RSI_5 extreme overbought ({rsi_5:.1f})')
        elif rsi_14 > 70:  # Standard overbought
            score += 0.2
            reasons.append(f'RSI_14 overbought ({rsi_14:.1f})')
        
        # Volume spike patterns
        if self.indicators.get('volume_spike_500'):  # 500% one-minute spike
            score += 0.35
            reasons.append('Volume spike 500% (1min)')
        elif self.indicators.get('volume_spike'):
            score += 0.2
            reasons.append('Volume spike')
        
        # MACD signals
        if self.indicators.get('macd_crossover') == 'bearish':
            score += 0.25
            reasons.append('MACD bearish crossover')
        if self.indicators.get('macd_divergence') == 'bearish':
            score += 0.3
            reasons.append('MACD bearish divergence')
        
        # EMA crossover
        if self.indicators.get('ema_crossover') == 'bearish':
            score += 0.25
            reasons.append('EMA 9/21 bearish crossover')
        
        # Bollinger Bands
        if self.indicators.get('bb_squeeze') and self.indicators.get('bb_squeeze_direction') == 'bearish':
            score += 0.3
            reasons.append('Bollinger Band squeeze breakdown (bearish)')
        elif self.indicators.get('bb_position') == 'above':
            score += 0.2
            reasons.append('Price above upper Bollinger Band')
        
        # Order book imbalance
        imbalance = self.indicators.get('order_book_imbalance', 0)
        if imbalance < -0.3:
            score += 0.2
            reasons.append(f'Strong sell pressure ({imbalance:.2f})')
        
        # Candlestick patterns
        if self.indicators.get('pattern_engulfing') == 'bearish':
            score += 0.2
            reasons.append('Bearish engulfing pattern')
        
        if self.indicators.get('pattern_pin_bar') == 'bearish':
            score += 0.15
            reasons.append('Bearish pin bar')
        
        if self.indicators.get('pattern_breakout') == 'bearish':
            score += 0.25
            reasons.append('Bearish breakdown')
        
        if self.indicators.get('pattern_trap') == 'high_trap':
            score += 0.2
            reasons.append('High trap (false breakout)')
        
        # Trend alignment bonus
        if self.indicators.get('trend_aligned') and self.indicators.get('aligned_trend') == 'bearish':
            score += 0.15
            reasons.append('Multi-timeframe bearish trend')
        
        # VWAP position
        if self.indicators.get('vwap'):
            current_price = market_data.get('ticker', {}).get('last', 0)
            vwap = self.indicators.get('vwap')
            if current_price > vwap * 1.005:  # Price above VWAP
                score += 0.15
                reasons.append('Price above VWAP')
        
        return score, reasons
    
    def _determine_strategy_type(self, market_data: Dict) -> str:
        """Determine trading strategy type based on market conditions."""
        # High volatility = wider targets
        atr_percent = self.indicators.get('atr_percent', 0)
        
        if atr_percent > 2.0:  # High volatility
            return 'swing'
        elif atr_percent > 1.0:  # Medium volatility
            return 'intraday'
        else:  # Low volatility
            return 'scalping'
    
    def _create_enhanced_entry_signal(self, side: str, confidence: float, reasons: List[str], 
                                    last: pd.Series, market_data: Dict, strategy_type: str) -> Dict:
        """Create enhanced entry signal with limit orders and dynamic stops."""
        # Get OHLCV data for dynamic stops
        timeframe_data = market_data.get('timeframes', {}).get(Config.DEFAULT_TIMEFRAME, {})
        df = timeframe_data.get('ohlcv')
        
        # Use ATR-based stops
        atr = self.indicators.get('atr_short', self.indicators.get('atr', last['close'] * 0.02))
        
        # Calculate dynamic stop loss based on local extremes
        stop_loss, sl_buffer = self._calculate_dynamic_stop_loss(df, side, atr)
        
        # Calculate entry price (market or limit with buffer)
        entry_price, order_type = self._calculate_entry_price(
            df, side, market_data, reasons
        )
        
        # Calculate take profits based on strategy type
        tp1_distance = self.TP1_LEVELS[strategy_type]
        tp2_distance = self.TP2_LEVELS[strategy_type]
        
        if side == 'long':
            tp1 = entry_price * (1 + tp1_distance)
            tp2 = entry_price * (1 + tp2_distance)
            take_profit = tp2  # Overall target
        else:
            tp1 = entry_price * (1 - tp1_distance)
            tp2 = entry_price * (1 - tp2_distance)
            take_profit = tp2  # Overall target
        
        # Time-based exit for scalping
        exit_time = None
        if strategy_type == 'scalping':
            exit_time = datetime.now() + timedelta(seconds=Config.SCALPING_MAX_HOLD_TIME)
        
        return {
            'action': 'OPEN',
            'side': side,
            'reason': f"{strategy_type.capitalize()} {side}: {', '.join(reasons)}",
            'entry_price': entry_price,
            'order_type': order_type,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'tp1': tp1,
            'tp2': tp2,
            'trailing_stop_activated': False,
            'tp1_hit': False,
            'exit_time': exit_time,
            'confidence': confidence,
            'indicators': self.indicators,
            'atr': atr,
            'spread': self.indicators.get('spread', 0.001),
            'strategy_type': strategy_type,
            'sl_buffer': sl_buffer,
            'emergency_exit_enabled': True
        }
    
    def _calculate_dynamic_stop_loss(self, df: pd.DataFrame, side: str, atr: float) -> Tuple[float, float]:
        """Calculate dynamic stop loss based on local extremes."""
        if df is None or len(df) < self.LOCAL_EXTREMES_LOOKBACK:
            # Fallback to ATR-based stop
            current_price = df['close'].iloc[-1] if df is not None else 0
            sl_buffer = atr * 1.5
            if side == 'long':
                return current_price * (1 - sl_buffer), sl_buffer
            else:
                return current_price * (1 + sl_buffer), sl_buffer
        
        # Find local extremes
        recent_data = df.iloc[-self.LOCAL_EXTREMES_LOOKBACK:]
        
        if side == 'long':
            # Find recent low
            local_low_idx = recent_data['low'].idxmin()
            local_low = recent_data.loc[local_low_idx, 'low']
            
            # Add buffer based on ATR
            sl_buffer = atr * 0.5
            stop_loss = local_low * (1 - sl_buffer)
            
        else:  # short
            # Find recent high
            local_high_idx = recent_data['high'].idxmax()
            local_high = recent_data.loc[local_high_idx, 'high']
            
            # Add buffer based on ATR
            sl_buffer = atr * 0.5
            stop_loss = local_high * (1 + sl_buffer)
        
        return stop_loss, sl_buffer
    
    def _calculate_entry_price(self, df: pd.DataFrame, side: str, 
                              market_data: Dict, reasons: List[str]) -> Tuple[float, str]:
        """Calculate entry price - market or limit with buffer."""
        current_price = market_data.get('ticker', {}).get('last', 0)
        
        # Check if this is a breakout signal
        is_breakout = any('breakout' in reason.lower() for reason in reasons)
        
        if is_breakout and df is not None and len(df) >= self.BREAKOUT_CONFIRMATION_BARS:
            # Use limit order with buffer for breakout confirmation
            if side == 'long':
                # Place limit order above breakout level
                resistance = self.indicators.get('resistance', current_price)
                entry_price = resistance * (1 + self.LIMIT_BUFFER)
                order_type = 'limit'
            else:
                # Place limit order below breakdown level
                support = self.indicators.get('support', current_price)
                entry_price = support * (1 - self.LIMIT_BUFFER)
                order_type = 'limit'
        else:
            # Use market order for immediate entry
            entry_price = current_price
            order_type = 'market'
        
        return entry_price, order_type
    
    def _check_exit_conditions(self, positions: List[Dict], market_data: Dict) -> Optional[Dict]:
        """Check for exit conditions with partial profit taking."""
        if not positions:
            return None
        
        timeframe_data = market_data.get('timeframes', {}).get(Config.DEFAULT_TIMEFRAME, {})
        df = timeframe_data.get('ohlcv')
        
        if df is None or df.empty:
            return None
        
        current_price = df['close'].iloc[-1]
        
        for position in positions:
            exit_conditions = []
            
            # Check if we should exit
            should_exit, exit_reason = self._should_exit_position(position, current_price, market_data)
            
            if should_exit:
                return {
                    'action': 'CLOSE',
                    'side': position['side'],
                    'reason': exit_reason,
                    'entry_price': current_price,
                    'confidence': 0.9,
                    'indicators': self.indicators
                }
        
        return None
    
    def _should_exit_position(self, position: Dict, current_price: float, market_data: Dict) -> tuple:
        """Determine if position should be exited including emergency conditions."""
        side = position['side']
        
        # Check emergency exit conditions first
        emergency_exit = self._check_emergency_exit(position, current_price, market_data)
        if emergency_exit[0]:
            return emergency_exit
        
        # Check stop loss
        if position.get('stop_loss'):
            if side == 'long' and current_price <= position['stop_loss']:
                return True, "Stop loss hit"
            elif side == 'short' and current_price >= position['stop_loss']:
                return True, "Stop loss hit"
        
        # Check take profit levels
        if position.get('tp1') and not position.get('tp1_hit'):
            if side == 'long' and current_price >= position['tp1']:
                # Mark TP1 as hit and activate trailing stop
                position['tp1_hit'] = True
                position['trailing_stop_activated'] = True
                return True, "First take profit reached (partial exit)"
            elif side == 'short' and current_price <= position['tp1']:
                position['tp1_hit'] = True
                position['trailing_stop_activated'] = True
                return True, "First take profit reached (partial exit)"
        
        # Check trailing stop if activated
        if position.get('trailing_stop_activated'):
            trailing_stop = self._calculate_trailing_stop(position, current_price)
            if trailing_stop[0]:
                return trailing_stop
        
        if position.get('tp2'):
            if side == 'long' and current_price >= position['tp2']:
                return True, "Final take profit reached"
            elif side == 'short' and current_price <= position['tp2']:
                return True, "Final take profit reached"
        
        # Check technical exit conditions
        technical_exit = self._check_technical_exit(position, market_data)
        if technical_exit:
            return True, technical_exit
        
        # Time-based exit
        if position.get('exit_time') and datetime.now() >= position['exit_time']:
            return True, "Time-based exit"
        
        return False, ""
    
    def _check_emergency_exit(self, position: Dict, current_price: float, 
                             market_data: Dict) -> Tuple[bool, str]:
        """Check for emergency exit conditions."""
        if not position.get('emergency_exit_enabled', True):
            return False, ""
        
        # Check for sudden volatility spike
        current_atr = self.indicators.get('atr', 0)
        position_atr = position.get('atr', current_atr)
        
        if position_atr > 0 and current_atr / position_atr > self.VOLATILITY_SPIKE_THRESHOLD:
            return True, "Emergency exit: Volatility spike"
        
        # Check for rapid price movement
        entry_price = position.get('entry_price', current_price)
        price_change = abs(current_price - entry_price) / entry_price
        
        if price_change > self.RAPID_PRICE_CHANGE:
            # Check if it happened too quickly (within 1 minute)
            position_age = (datetime.now() - position.get('opened_at', datetime.now())).total_seconds()
            if position_age < 60:
                return True, "Emergency exit: Rapid price movement"
        
        # Check for extreme order book imbalance (potential manipulation)
        imbalance = abs(self.indicators.get('order_book_imbalance', 0))
        if imbalance > 0.8:
            return True, "Emergency exit: Extreme order book imbalance"
        
        # Check for funding rate spike (for futures)
        funding_rate = abs(self.indicators.get('funding_rate', 0))
        if funding_rate > 0.1:  # 10% funding rate
            return True, "Emergency exit: Extreme funding rate"
        
        return False, ""
    
    def _calculate_trailing_stop(self, position: Dict, current_price: float) -> Tuple[bool, str]:
        """Calculate and check trailing stop."""
        side = position['side']
        entry_price = position.get('entry_price', current_price)
        
        # Calculate profit percentage
        if side == 'long':
            profit_pct = (current_price - entry_price) / entry_price
            trailing_stop = current_price * (1 - self.TRAILING_STOP_DISTANCE)
            
            # Update trailing stop if price moved favorably
            if 'trailing_stop_price' not in position:
                position['trailing_stop_price'] = trailing_stop
            else:
                position['trailing_stop_price'] = max(position['trailing_stop_price'], trailing_stop)
            
            # Check if trailing stop hit
            if current_price <= position['trailing_stop_price']:
                return True, "Trailing stop hit"
                
        else:  # short
            profit_pct = (entry_price - current_price) / entry_price
            trailing_stop = current_price * (1 + self.TRAILING_STOP_DISTANCE)
            
            # Update trailing stop if price moved favorably
            if 'trailing_stop_price' not in position:
                position['trailing_stop_price'] = trailing_stop
            else:
                position['trailing_stop_price'] = min(position['trailing_stop_price'], trailing_stop)
            
            # Check if trailing stop hit
            if current_price >= position['trailing_stop_price']:
                return True, "Trailing stop hit"
        
        return False, ""
    
    def _check_technical_exit(self, position: Dict, market_data: Dict) -> Optional[str]:
        """Check for technical exit signals."""
        side = position['side']
        
        # RSI exit conditions
        rsi_5 = self.indicators.get('rsi_5', 50)
        
        if side == 'long':
            if rsi_5 > 70:
                return "RSI_5 overbought exit"
            
            # Trend reversal
            if self.indicators.get('ema_crossover') == 'bearish':
                return "EMA bearish crossover"
            
            # Bearish pattern
            if self.indicators.get('pattern_engulfing') == 'bearish':
                return "Bearish engulfing pattern"
            
            # MACD exit
            if self.indicators.get('macd_crossover') == 'bearish':
                return "MACD bearish crossover"
                
        elif side == 'short':
            if rsi_5 < 30:
                return "RSI_5 oversold exit"
            
            # Trend reversal
            if self.indicators.get('ema_crossover') == 'bullish':
                return "EMA bullish crossover"
            
            # Bullish pattern
            if self.indicators.get('pattern_engulfing') == 'bullish':
                return "Bullish engulfing pattern"
            
            # MACD exit
            if self.indicators.get('macd_crossover') == 'bullish':
                return "MACD bullish crossover"
        
        return None
    
    def modify_position(self, position: Dict, market_data: Dict) -> Dict:
        """Modify existing position based on changing market conditions."""
        modifications = {
            'modify_stop_loss': False,
            'modify_take_profit': False,
            'close_position': False,
            'new_stop_loss': None,
            'new_take_profit': None,
            'reason': ''
        }
        
        # Get current market data
        timeframe_data = market_data.get('timeframes', {}).get(Config.DEFAULT_TIMEFRAME, {})
        df = timeframe_data.get('ohlcv')
        
        if df is None or df.empty:
            return modifications
        
        current_price = df['close'].iloc[-1]
        side = position['side']
        
        # Recalculate indicators
        self.indicators = self.indicators_calculator.calculate_all_indicators(df)
        
        # Check if trend has changed significantly
        current_trend = self.indicators.get('trend', 'neutral')
        entry_trend = position.get('entry_trend', current_trend)
        
        if side == 'long' and current_trend in ['bearish', 'strong_bearish']:
            modifications['close_position'] = True
            modifications['reason'] = 'Trend reversal to bearish'
            return modifications
        elif side == 'short' and current_trend in ['bullish', 'strong_bullish']:
            modifications['close_position'] = True
            modifications['reason'] = 'Trend reversal to bullish'
            return modifications
        
        # Adjust stop loss based on new support/resistance
        if position.get('tp1_hit') and not position.get('trailing_stop_activated'):
            # Move stop loss to breakeven after TP1 hit
            modifications['modify_stop_loss'] = True
            modifications['new_stop_loss'] = position['entry_price']
            modifications['reason'] = 'Move stop loss to breakeven after TP1'
        
        # Adjust take profit if volatility changed significantly
        current_atr = self.indicators.get('atr', 0)
        position_atr = position.get('atr', current_atr)
        
        if position_atr > 0 and abs(current_atr - position_atr) / position_atr > 0.5:
            # Volatility changed by more than 50%
            modifications['modify_take_profit'] = True
            
            # Recalculate TP based on new volatility
            strategy_type = position.get('strategy_type', 'scalping')
            tp2_distance = self.TP2_LEVELS[strategy_type]
            
            if current_atr > position_atr:
                # Increase TP if volatility increased
                tp2_distance *= 1.5
            else:
                # Decrease TP if volatility decreased
                tp2_distance *= 0.75
            
            if side == 'long':
                modifications['new_take_profit'] = position['entry_price'] * (1 + tp2_distance)
            else:
                modifications['new_take_profit'] = position['entry_price'] * (1 - tp2_distance)
            
            modifications['reason'] += ' Adjust TP for volatility change'
        
        return modifications
    
    def _empty_signal(self) -> Dict:
        """Return empty signal structure."""
        return {
            'action': None,
            'side': None,
            'reason': '',
            'entry_price': 0,
            'order_type': 'market',
            'stop_loss': None,
            'take_profit': None,
            'confidence': 0.0,
            'indicators': {}
        }