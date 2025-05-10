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
        """Oblicza wskaźniki techniczne dla skalpowania"""
        # RSI dla różnych okresów (5-10)
        df['rsi_5'] = ta.momentum.RSIIndicator(close=df['close'], window=5).rsi()
        df['rsi_7'] = ta.momentum.RSIIndicator(close=df['close'], window=7).rsi()
        df['rsi_10'] = ta.momentum.RSIIndicator(close=df['close'], window=10).rsi()
        df['rsi_14'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        
        # VWAP (Volume-Weighted Average Price)
        df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        
        # ATR dla zmienności
        df['atr'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
        df['atr_5'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=5).average_true_range()
        
        # EMA
        df['ema_fast'] = ta.trend.EMAIndicator(close=df['close'], window=Config.EMA_FAST).ema_indicator()
        df['ema_slow'] = ta.trend.EMAIndicator(close=df['close'], window=Config.EMA_SLOW).ema_indicator()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_lower'] = bollinger.bollinger_lband()
        df['bb_middle'] = bollinger.bollinger_mavg()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # MACD
        macd = ta.trend.MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Volatility
        df['volatility'] = df['close'].pct_change().rolling(window=20).std() * np.sqrt(20)
        
        # Volume analysis
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def calculate_volume_features(self, df):
        """Oblicza cechy związane z nagłymi zmianami wolumenu"""
        # Podstawowe statystyki wolumenu
        df['volume_ma_5'] = df['volume'].rolling(window=5).mean()
        df['volume_ma_20'] = df['volume'].rolling(window=20).mean()
        
        # Detekcja skoków wolumenu (500% wzrost w 1 minutę)
        df['volume_spike'] = df['volume'] / df['volume'].shift(1)
        df['volume_spike_500'] = df['volume_spike'] > 5.0
        
        # Detekcja skoków względem średniej
        df['volume_spike_ma'] = df['volume'] / df['volume_ma_20']
        df['volume_spike_extreme'] = df['volume_spike_ma'] > 3.0  # 300% powyżej średniej
        
        # Analiza kierunku wolumenu (buy vs sell volume)
        df['price_change'] = df['close'] - df['open']
        df['buy_volume'] = df['volume'].where(df['price_change'] > 0, 0)
        df['sell_volume'] = df['volume'].where(df['price_change'] < 0, 0)
        
        # Volume momentum
        df['volume_momentum'] = df['volume'].rolling(window=5).mean() / df['volume'].rolling(window=20).mean()
        
        # Cumulative volume delta
        df['volume_delta'] = df['buy_volume'] - df['sell_volume']
        df['cumulative_volume_delta'] = df['volume_delta'].cumsum()
        
        return df
    
    def calculate_session_features(self, df):
        """Oblicza cechy związane z sesjami handlowymi"""
        # Konwertuj timestamp do UTC jeśli nie jest
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC')
        
        # Godzina w UTC
        df['hour_utc'] = df['timestamp'].dt.hour
        df['minute_utc'] = df['timestamp'].dt.minute
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        # Sesje handlowe (w UTC)
        # Azja: 00:00 - 08:00 UTC
        # Europa: 07:00 - 16:00 UTC  
        # USA: 13:00 - 22:00 UTC
        
        df['session_asia'] = ((df['hour_utc'] >= 0) & (df['hour_utc'] < 8)).astype(int)
        df['session_europe'] = ((df['hour_utc'] >= 7) & (df['hour_utc'] < 16)).astype(int)
        df['session_usa'] = ((df['hour_utc'] >= 13) & (df['hour_utc'] < 22)).astype(int)
        
        # Overlap sessions
        df['session_asia_europe'] = ((df['hour_utc'] >= 7) & (df['hour_utc'] < 8)).astype(int)
        df['session_europe_usa'] = ((df['hour_utc'] >= 13) & (df['hour_utc'] < 16)).astype(int)
        
        # Najwyższa płynność - gdy Europa i USA są aktywne
        df['high_liquidity_hours'] = ((df['hour_utc'] >= 13) & (df['hour_utc'] < 16)).astype(int)
        
        # Weekend detection
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Time-based features
        df['minutes_since_day_start'] = df['hour_utc'] * 60 + df['minute_utc']
        df['minutes_until_day_end'] = 1440 - df['minutes_since_day_start']
        
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
            try:
                self.current_sentiment = self.sentiment_analyzer.get_overall_sentiment()
                self.last_sentiment_update = current_time
                self.logger.info(f"Updated sentiment: {self.current_sentiment['sentiment_signal']} ({self.current_sentiment['overall_sentiment']:.2f})")
            except Exception as e:
                self.logger.warning(f"Could not update sentiment: {e}")
                # Domyślny sentyment jeśli brak API
                self.current_sentiment = {'overall_sentiment': 0, 'sentiment_signal': 'neutral'}
    
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
        """Generuje sygnały tradingowe z uwzględnieniem nowych cech"""
        if df is None or len(df) < 50:
            return {'action': None, 'reason': 'Insufficient data'}
        
        # Oblicz wszystkie wskaźniki i cechy
        df = self.calculate_indicators(df)
        df = self.calculate_volume_features(df)
        df = self.calculate_session_features(df)
        
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
                'rsi_5': last['rsi_5'],
                'rsi_7': last['rsi_7'],
                'rsi_10': last['rsi_10'],
                'rsi_14': last['rsi_14'],
                'vwap': last['vwap'],
                'price_vs_vwap': (last['close'] - last['vwap']) / last['vwap'] * 100,
                'ema_fast': last['ema_fast'],
                'ema_slow': last['ema_slow'],
                'trend': self.check_trend(df),
                'volume_ratio': last['volume_ratio'],
                'volume_spike_500': last['volume_spike_500'],
                'volume_spike_extreme': last['volume_spike_extreme'],
                'macd': last['macd'],
                'macd_signal': last['macd_signal'],
                'volatility': last['volatility'],
                'atr_5': last['atr_5'],
                'bb_width': last['bb_width'],
                'sentiment': self.current_sentiment['sentiment_signal'],
                'sentiment_score': self.current_sentiment['overall_sentiment'],
                'order_book_imbalance': order_book_analysis['imbalance'],
                'spread': order_book_analysis['spread'],
                'liquidity': order_book_analysis['liquidity']['total_liquidity'],
                'session': 'asia' if last['session_asia'] else 'europe' if last['session_europe'] else 'usa' if last['session_usa'] else 'other',
                'high_liquidity_hours': last['high_liquidity_hours'],
                'hour_utc': last['hour_utc']
            }
        }
        
        # Sprawdź warunki rynkowe
        if order_book_analysis['spread'] > 0.5:  # Zbyt duży spread
            signal['reason'] = 'Spread too high'
            return signal
        
        if order_book_analysis['liquidity']['total_liquidity'] < Config.LIQUIDITY_MIN_THRESHOLD:
            signal['reason'] = 'Insufficient liquidity'
            return signal
        
        trend = self.check_trend(df)
        
        # === ENHANCED SCALPING SIGNALS ===
        long_conditions = []
        short_conditions = []
        
        # Warunki dla LONG
        # 1. RSI oversold na krótkim okresie
        if last['rsi_5'] < 25 or last['rsi_7'] < 27:
            long_conditions.append(('extreme_oversold_scalp', 0.3))
        
        # 2. Price below VWAP + bounce
        if last['close'] < last['vwap'] and last['close'] > prev['close']:
            long_conditions.append(('vwap_bounce', 0.25))
        
        # 3. Volume spike with price increase
        if last['volume_spike_500'] and last['close'] > prev['close']:
            long_conditions.append(('volume_spike_buy', 0.35))
        
        # 4. High liquidity hours bonus
        if last['high_liquidity_hours']:
            long_conditions.append(('high_liquidity', 0.1))
        
        # 5. Order book imbalance
        if order_book_analysis['imbalance'] > Config.ORDER_BOOK_IMBALANCE_THRESHOLD:
            long_conditions.append(('order_book_buy_pressure', 0.3))
        
        # 6. Bullish divergence (price down, RSI up)
        if last['close'] < prev['close'] and last['rsi_5'] > prev['rsi_5']:
            long_conditions.append(('bullish_divergence', 0.25))
        
        # Warunki dla SHORT
        # 1. RSI overbought na krótkim okresie
        if last['rsi_5'] > 75 or last['rsi_7'] > 73:
            short_conditions.append(('extreme_overbought_scalp', 0.3))
        
        # 2. Price above VWAP + rejection
        if last['close'] > last['vwap'] and last['close'] < prev['close']:
            short_conditions.append(('vwap_rejection', 0.25))
        
        # 3. Volume spike with price decrease
        if last['volume_spike_500'] and last['close'] < prev['close']:
            short_conditions.append(('volume_spike_sell', 0.35))
        
        # 4. High liquidity hours bonus
        if last['high_liquidity_hours']:
            short_conditions.append(('high_liquidity', 0.1))
        
        # 5. Order book imbalance
        if order_book_analysis['imbalance'] < -Config.ORDER_BOOK_IMBALANCE_THRESHOLD:
            short_conditions.append(('order_book_sell_pressure', 0.3))
        
        # 6. Bearish divergence (price up, RSI down)
        if last['close'] > prev['close'] and last['rsi_5'] < prev['rsi_5']:
            short_conditions.append(('bearish_divergence', 0.25))
        
        # Oblicz całkowitą pewność dla LONG
        if long_conditions and trend != 'bearish':
            total_confidence = sum(weight for _, weight in long_conditions)
            reasons = ', '.join(reason for reason, _ in long_conditions)
            
            if total_confidence >= 0.7:
                signal['action'] = 'OPEN'
                signal['side'] = 'long'
                signal['reason'] = f'Scalp long: {reasons}'
                signal['confidence'] = total_confidence
                
                # Dynamic stop loss based on ATR and volatility
                atr_multiplier = 1.0 if last['high_liquidity_hours'] else 1.5
                signal['stop_loss'] = last['close'] - (last['atr_5'] * atr_multiplier)
                signal['take_profit'] = last['close'] + (last['atr_5'] * 2.0)
                signal['scalp_trade'] = True
        
        # Oblicz całkowitą pewność dla SHORT
        elif short_conditions and trend != 'bullish':
            total_confidence = sum(weight for _, weight in short_conditions)
            reasons = ', '.join(reason for reason, _ in short_conditions)
            
            if total_confidence >= 0.7:
                signal['action'] = 'OPEN'
                signal['side'] = 'short'
                signal['reason'] = f'Scalp short: {reasons}'
                signal['confidence'] = total_confidence
                
                # Dynamic stop loss
                atr_multiplier = 1.0 if last['high_liquidity_hours'] else 1.5
                signal['stop_loss'] = last['close'] + (last['atr_5'] * atr_multiplier)
                signal['take_profit'] = last['close'] - (last['atr_5'] * 2.0)
                signal['scalp_trade'] = True
        
        # === EXIT SIGNALS ===
        for position in existing_positions:
            exit_conditions = []
            
            if position['side'] == 'long':
                # Quick exit na ekstremalnym RSI
                if last['rsi_5'] > 70:
                    exit_conditions.append('RSI_5 extreme overbought')
                
                # Exit na VWAP
                if last['close'] > last['vwap'] * 1.005:  # 0.5% powyżej VWAP
                    exit_conditions.append('Price above VWAP target')
                
                # Volume exhaustion
                if prev['volume_spike_500'] and last['volume'] < last['volume_ma_5']:
                    exit_conditions.append('Volume exhaustion')
                
                # Time-based exit dla scalping
                if position.get('scalp_trade'):
                    hold_time = (datetime.now() - position.get('opened_at', datetime.now())).total_seconds()
                    if hold_time > 300:  # 5 minut
                        exit_conditions.append('Scalp time limit')
            
            elif position['side'] == 'short':
                # Quick exit na ekstremalnym RSI
                if last['rsi_5'] < 30:
                    exit_conditions.append('RSI_5 extreme oversold')
                
                # Exit na VWAP
                if last['close'] < last['vwap'] * 0.995:  # 0.5% poniżej VWAP
                    exit_conditions.append('Price below VWAP target')
                
                # Volume exhaustion
                if prev['volume_spike_500'] and last['volume'] < last['volume_ma_5']:
                    exit_conditions.append('Volume exhaustion')
                
                # Time-based exit
                if position.get('scalp_trade'):
                    hold_time = (datetime.now() - position.get('opened_at', datetime.now())).total_seconds()
                    if hold_time > 300:  # 5 minut
                        exit_conditions.append('Scalp time limit')
            
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