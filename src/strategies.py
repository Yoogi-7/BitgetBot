# src/strategies.py
import pandas as pd
import ta
from config.settings import Config
import logging
import numpy as np
from src.order_book_analyzer import OrderBookAnalyzer
from src.sentiment_analyzer import SentimentAnalyzer

class EnhancedFuturesStrategy:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.order_book_analyzer = OrderBookAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.last_sentiment_update = 0
        self.current_sentiment = {'overall_sentiment': 0, 'sentiment_signal': 'neutral'}
    
    def calculate_indicators(self, df):
        """Oblicza wskaźniki techniczne"""
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=Config.RSI_PERIOD).rsi()
        
        # EMA
        df['ema_fast'] = ta.trend.EMAIndicator(close=df['close'], window=Config.EMA_FAST).ema_indicator()
        df['ema_slow'] = ta.trend.EMAIndicator(close=df['close'], window=Config.EMA_SLOW).ema_indicator()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_lower'] = bollinger.bollinger_lband()
        df['bb_middle'] = bollinger.bollinger_mavg()
        
        # ATR
        df['atr'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close']).average_true_range()
        
        # Volume
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        # MACD
        macd = ta.trend.MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Volatility
        df['volatility'] = df['close'].pct_change().rolling(window=20).std() * np.sqrt(20)
        
        return df
    
    def check_trend(self, df):
        """Sprawdza kierunek trendu"""
        last = df.iloc[-1]
        
        if last['ema_fast'] > last['ema_slow'] and last['close'] > last['ema_fast']:
            return 'bullish'
        elif last['ema_fast'] < last['ema_slow'] and last['close'] < last['ema_fast']:
            return 'bearish'
        else:
            return 'neutral'
    
    def update_sentiment(self):
        """Aktualizuje dane sentymentu"""
        import time
        current_time = time.time()
        
        # Aktualizuj tylko jeśli minął odpowiedni czas
        if current_time - self.last_sentiment_update > Config.SENTIMENT_UPDATE_INTERVAL:
            self.current_sentiment = self.sentiment_analyzer.get_overall_sentiment()
            self.last_sentiment_update = current_time
            self.logger.info(f"Updated sentiment: {self.current_sentiment['sentiment_signal']} ({self.current_sentiment['overall_sentiment']:.2f})")
    
    def analyze_order_book(self, order_book, trade_size):
        """Analizuje order book"""
        if not order_book:
            return {
                'spread': 0,
                'liquidity': {'total_liquidity': 0},
                'imbalance': 0,
                'slippage': {'slippage_pct': 0},
                'large_orders': {'large_bids': [], 'large_asks': []}
            }
        
        spread = self.order_book_analyzer.calculate_spread(order_book)
        liquidity = self.order_book_analyzer.calculate_liquidity(order_book)
        imbalance = self.order_book_analyzer.calculate_order_book_imbalance(order_book)
        slippage_buy = self.order_book_analyzer.calculate_slippage(order_book, trade_size, 'buy')
        slippage_sell = self.order_book_analyzer.calculate_slippage(order_book, trade_size, 'sell')
        large_orders = self.order_book_analyzer.detect_large_orders(order_book, Config.LARGE_ORDER_MULTIPLIER)
        
        return {
            'spread': spread,
            'liquidity': liquidity,
            'imbalance': imbalance,
            'slippage_buy': slippage_buy,
            'slippage_sell': slippage_sell,
            'large_orders': large_orders
        }
    
    def generate_signal(self, df, existing_positions=[], order_book=None, recent_trades=None):
        """Generuje sygnały tradingowe z uwzględnieniem order book i sentymentu"""
        if df is None or len(df) < 50:
            return {'action': None, 'reason': 'Insufficient data'}
        
        df = self.calculate_indicators(df)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Aktualizuj sentyment
        self.update_sentiment()
        
        # Analiza order book
        order_book_analysis = self.analyze_order_book(order_book, Config.TRADE_AMOUNT_USDT)
        
        signal = {
            'action': None,
            'side': None,
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
                'volume_ratio': last['volume'] / last['volume_sma'] if last['volume_sma'] > 0 else 1,
                'macd': last['macd'],
                'macd_signal': last['macd_signal'],
                'volatility': last['volatility'],
                'sentiment': self.current_sentiment['sentiment_signal'],
                'sentiment_score': self.current_sentiment['overall_sentiment'],
                'order_book_imbalance': order_book_analysis['imbalance'],
                'spread': order_book_analysis['spread'],
                'liquidity': order_book_analysis['liquidity']['total_liquidity']
            }
        }
        
        # Sprawdź warunki rynkowe
        if order_book_analysis['spread'] > 0.5:  # Zbyt duży spread
            signal['reason'] = 'Spread too high'
            return signal
        
        if order_book_analysis['liquidity']['total_liquidity'] < Config.LIQUIDITY_MIN_THRESHOLD:
            signal['reason'] = 'Insufficient liquidity'
            return signal
        
        # Sprawdź czy wolumen jest wystarczający
        if last['volume'] < last['volume_sma'] * Config.MIN_VOLUME_MULTIPLIER:
            signal['reason'] = 'Low volume'
            return signal
        
        trend = self.check_trend(df)
        
        # === ENHANCED LONG SIGNALS ===
        if trend == 'bullish':
            long_conditions = []
            
            # RSI Oversold Bounce
            if last['rsi'] < Config.RSI_OVERSOLD and prev['rsi'] >= Config.RSI_OVERSOLD:
                long_conditions.append(('rsi_oversold', 0.3))
            
            # Bollinger Band Bounce
            if last['low'] <= last['bb_lower'] and last['close'] > last['bb_lower']:
                long_conditions.append(('bb_bounce', 0.25))
            
            # MACD Crossover
            if last['macd'] > last['macd_signal'] and prev['macd'] <= prev['macd_signal']:
                long_conditions.append(('macd_cross', 0.25))
            
            # Order Book Imbalance (więcej bid orders)
            if order_book_analysis['imbalance'] > Config.ORDER_BOOK_IMBALANCE_THRESHOLD:
                long_conditions.append(('order_book_buy_pressure', 0.2))
            
            # Positive sentiment
            if self.current_sentiment['sentiment_signal'] == 'bullish':
                long_conditions.append(('bullish_sentiment', Config.SENTIMENT_WEIGHT))
            
            # Large bid orders detected
            if len(order_book_analysis['large_orders']['large_bids']) > 0:
                long_conditions.append(('large_bid_support', 0.15))
            
            # Oblicz całkowitą pewność
            if long_conditions:
                total_confidence = sum(weight for _, weight in long_conditions)
                reasons = ', '.join(reason for reason, _ in long_conditions)
                
                if total_confidence >= 0.7:
                    signal['action'] = 'OPEN'
                    signal['side'] = 'long'
                    signal['reason'] = f'Bullish signals: {reasons}'
                    signal['confidence'] = total_confidence
                    
                    # Dynamic stop loss based on volatility and liquidity
                    volatility_multiplier = min(2.0, max(1.0, last['volatility'] * 10))
                    signal['stop_loss'] = last['close'] - (last['atr'] * volatility_multiplier)
                    signal['take_profit'] = last['close'] + (last['atr'] * 2.5)
        
        # === ENHANCED SHORT SIGNALS ===
        elif trend == 'bearish':
            short_conditions = []
            
            # RSI Overbought Reversal
            if last['rsi'] > Config.RSI_OVERBOUGHT and prev['rsi'] <= Config.RSI_OVERBOUGHT:
                short_conditions.append(('rsi_overbought', 0.3))
            
            # Bollinger Band Rejection
            if last['high'] >= last['bb_upper'] and last['close'] < last['bb_upper']:
                short_conditions.append(('bb_rejection', 0.25))
            
            # MACD Crossover
            if last['macd'] < last['macd_signal'] and prev['macd'] >= prev['macd_signal']:
                short_conditions.append(('macd_cross', 0.25))
            
            # Order Book Imbalance (więcej ask orders)
            if order_book_analysis['imbalance'] < -Config.ORDER_BOOK_IMBALANCE_THRESHOLD:
                short_conditions.append(('order_book_sell_pressure', 0.2))
            
            # Negative sentiment
            if self.current_sentiment['sentiment_signal'] == 'bearish':
                short_conditions.append(('bearish_sentiment', Config.SENTIMENT_WEIGHT))
            
            # Large ask orders detected
            if len(order_book_analysis['large_orders']['large_asks']) > 0:
                short_conditions.append(('large_ask_resistance', 0.15))
            
            # Oblicz całkowitą pewność
            if short_conditions:
                total_confidence = sum(weight for _, weight in short_conditions)
                reasons = ', '.join(reason for reason, _ in short_conditions)
                
                if total_confidence >= 0.7:
                    signal['action'] = 'OPEN'
                    signal['side'] = 'short'
                    signal['reason'] = f'Bearish signals: {reasons}'
                    signal['confidence'] = total_confidence
                    
                    # Dynamic stop loss
                    volatility_multiplier = min(2.0, max(1.0, last['volatility'] * 10))
                    signal['stop_loss'] = last['close'] + (last['atr'] * volatility_multiplier)
                    signal['take_profit'] = last['close'] - (last['atr'] * 2.5)
        
        # === HIGH FREQUENCY SCALPING SIGNALS ===
        if Config.HFT_ENABLED:
            # Quick scalping na ekstremalnych warunkach
            if last['rsi'] < 25 and order_book_analysis['imbalance'] > 0.5:
                signal['action'] = 'OPEN'
                signal['side'] = 'long'
                signal['reason'] = 'HFT: Extreme oversold with buy pressure'
                signal['confidence'] = 0.85
                signal['stop_loss'] = last['close'] - (last['atr'] * 0.5)
                signal['take_profit'] = last['close'] + (last['atr'] * 1.0)
                signal['hft_trade'] = True
            
            elif last['rsi'] > 75 and order_book_analysis['imbalance'] < -0.5:
                signal['action'] = 'OPEN'
                signal['side'] = 'short'
                signal['reason'] = 'HFT: Extreme overbought with sell pressure'
                signal['confidence'] = 0.85
                signal['stop_loss'] = last['close'] + (last['atr'] * 0.5)
                signal['take_profit'] = last['close'] - (last['atr'] * 1.0)
                signal['hft_trade'] = True
        
        # === EXIT SIGNALS ===
        for position in existing_positions:
            exit_conditions = []
            
            if position['side'] == 'long':
                # Technical exit signals
                if last['rsi'] > Config.RSI_OVERBOUGHT:
                    exit_conditions.append('RSI overbought')
                
                if trend == 'bearish':
                    exit_conditions.append('Trend changed to bearish')
                
                if last['macd'] < last['macd_signal']:
                    exit_conditions.append('MACD bearish cross')
                
                # Order book exit signals
                if order_book_analysis['imbalance'] < -0.3:
                    exit_conditions.append('Strong sell pressure in order book')
                
                # Sentiment exit
                if self.current_sentiment['sentiment_signal'] == 'bearish':
                    exit_conditions.append('Sentiment turned bearish')
                
                # HFT quick exit
                if position.get('hft_trade') and position.get('unrealized_pnl', 0) > 0:
                    pnl_percent = (position['unrealized_pnl'] / position['size_usd']) * 100
                    if pnl_percent >= Config.HFT_MIN_PROFIT_PERCENT:
                        exit_conditions.append('HFT minimum profit reached')
            
            elif position['side'] == 'short':
                # Technical exit signals
                if last['rsi'] < Config.RSI_OVERSOLD:
                    exit_conditions.append('RSI oversold')
                
                if trend == 'bullish':
                    exit_conditions.append('Trend changed to bullish')
                
                if last['macd'] > last['macd_signal']:
                    exit_conditions.append('MACD bullish cross')
                
                # Order book exit signals
                if order_book_analysis['imbalance'] > 0.3:
                    exit_conditions.append('Strong buy pressure in order book')
                
                # Sentiment exit
                if self.current_sentiment['sentiment_signal'] == 'bullish':
                    exit_conditions.append('Sentiment turned bullish')
                
                # HFT quick exit
                if position.get('hft_trade') and position.get('unrealized_pnl', 0) > 0:
                    pnl_percent = (position['unrealized_pnl'] / position['size_usd']) * 100
                    if pnl_percent >= Config.HFT_MIN_PROFIT_PERCENT:
                        exit_conditions.append('HFT minimum profit reached')
            
            if exit_conditions:
                signal['action'] = 'CLOSE'
                signal['side'] = position['side']
                signal['reason'] = 'Exit: ' + ', '.join(exit_conditions)
                signal['confidence'] = 0.9
                break
        
        return signal
    
    def calculate_position_size(self, account_balance, entry_price, stop_loss_price, order_book_analysis):
        """Oblicza wielkość pozycji na podstawie ryzyka i płynności"""
        risk_amount = account_balance * 0.01  # 1% ryzyka na trade
        price_difference = abs(entry_price - stop_loss_price)
        position_size = risk_amount / price_difference
        
        # Ogranicz na podstawie płynności
        if order_book_analysis and 'liquidity' in order_book_analysis:
            max_liquidity_size = order_book_analysis['liquidity']['total_liquidity'] * 0.1  # Max 10% płynności
            position_size_usd = position_size * entry_price
            
            if position_size_usd > max_liquidity_size:
                position_size = max_liquidity_size / entry_price
        
        # Ogranicz do maksymalnej wielkości
        max_position = Config.MAX_POSITION_SIZE / entry_price
        return min(position_size, max_position)