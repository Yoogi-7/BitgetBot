# src/trading_bot.py
import logging
import time
from datetime import datetime
from config.settings import Config
from src.data_collector import DataCollector
from src.strategies import EnhancedFuturesStrategy
from src.trade_logger import TradeLogger
from src.telegram_notifier import TelegramNotifier

class EnhancedBitgetTradingBot:
    def __init__(self):
        self.data_collector = DataCollector()
        self.strategy = EnhancedFuturesStrategy()
        self.trade_logger = TradeLogger()
        self.telegram = TelegramNotifier()
        self.logger = logging.getLogger(__name__)
        
        # Stan bota
        self.daily_pnl = 0
        self.trades_today = 0
        self.startup_time = datetime.now()
        
        # Paper trading state
        if Config.PAPER_TRADING:
            self.paper_positions = []
            self.paper_balance = 1000.0
            self.paper_trades = []
        
        # High frequency tracking
        self.last_trade_time = 0
        self.hft_positions = []
        
        # Inicjalizacja
        self.initialize()
    
    def initialize(self):
        """Inicjalizacja bota"""
        try:
            # Ustaw dźwignię
            self.data_collector.set_leverage(Config.TRADING_SYMBOL, Config.LEVERAGE)
            
            # Sprawdź saldo
            balance = self.data_collector.get_futures_balance()
            if balance:
                if Config.PAPER_TRADING:
                    self.logger.info(f"[PAPER TRADING] Starting balance: {balance['available']} USDT")
                else:
                    self.logger.info(f"Account balance: {balance['available']} USDT")
            
            # Sprawdź otwarte pozycje
            positions = self.get_positions()
            if positions:
                self.logger.info(f"Open positions: {len(positions)}")
                for pos in positions:
                    self.logger.info(f"Position: {pos['side']} {pos.get('notional', 0)} USDT @ {pos.get('entry_price', 0)}")
            
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
    
    def get_positions(self):
        """Pobiera pozycje (prawdziwe lub paper)"""
        if Config.PAPER_TRADING:
            return self.paper_positions
        else:
            return self.data_collector.get_positions()
    
    def check_risk_limits(self):
        """Sprawdza limity ryzyka"""
        # Sprawdź dzienny limit strat
        if self.daily_pnl <= -Config.MAX_DAILY_LOSS:
            self.logger.warning(f"Daily loss limit reached: {self.daily_pnl} USDT")
            return False
        
        # Sprawdź liczbę otwartych pozycji
        positions = self.get_positions()
        if len(positions) >= Config.MAX_OPEN_POSITIONS:
            self.logger.info(f"Maximum open positions reached: {len(positions)}")
            return False
        
        return True
    
    def place_order(self, side, amount, price=None, order_type='market', reduce_only=False):
        """Składa zlecenie (prawdziwe lub paper)"""
        try:
            if Config.PAPER_TRADING:
                # Symuluj zlecenie
                self.logger.info(f"[PAPER] Order placed: {side} {amount} BTC @ {price or 'market'}")
                
                # Dla paper trading od razu "wykonaj" zlecenie
                if price is None:
                    ticker = self.data_collector.get_ticker()
                    price = ticker['last'] if ticker else 0
                
                return {
                    'id': f"paper_{datetime.now().timestamp()}",
                    'status': 'closed',
                    'price': price,
                    'amount': amount,
                    'side': side,
                    'reduce_only': reduce_only
                }
            else:
                # Prawdziwe zlecenie
                exchange = self.data_collector.exchange
                symbol = Config.TRADING_SYMBOL
                
                params = {
                    'reduceOnly': reduce_only
                }
                
                if order_type == 'market':
                    order = exchange.create_market_order(symbol, side, amount, params=params)
                else:
                    order = exchange.create_limit_order(symbol, side, amount, price, params=params)
                
                self.logger.info(f"Order placed: {side} {amount} {symbol}")
                return order
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
    def open_position(self, signal):
        """Otwiera nową pozycję"""
        try:
            if Config.PAPER_TRADING:
                balance = self.paper_balance
            else:
                balance_data = self.data_collector.get_futures_balance()
                balance = balance_data['available'] if balance_data else 0
            
            if balance <= 0:
                self.logger.warning("Insufficient balance")
                return
            
            entry_price = signal['entry_price']
            
            # Oblicz wielkość pozycji
            position_size_usd = min(Config.TRADE_AMOUNT_USDT, balance * 0.95)
            position_size_btc = position_size_usd / entry_price
            
            # Złóż zlecenie
            side = 'buy' if signal['side'] == 'long' else 'sell'
            order = self.place_order(side, position_size_btc)
            
            if order:
                self.logger.info(f"{'[PAPER] ' if Config.PAPER_TRADING else ''}Opened {signal['side']} position: {position_size_usd:.2f} USDT")
                
                if Config.PAPER_TRADING:
                    # Dodaj pozycję do paper positions
                    paper_position = {
                        'id': order['id'],
                        'symbol': Config.TRADING_SYMBOL,
                        'side': signal['side'],
                        'size': position_size_btc,
                        'notional': position_size_usd,
                        'entry_price': entry_price,
                        'mark_price': entry_price,
                        'unrealized_pnl': 0,
                        'stop_loss': signal.get('stop_loss'),
                        'take_profit': signal.get('take_profit'),
                        'opened_at': datetime.now(),
                        'scalp_trade': signal.get('scalp_trade', False),
                        'hft_trade': signal.get('hft_trade', False)
                    }
                    self.paper_positions.append(paper_position)
                    self.paper_balance -= position_size_usd
                    
                    # Zapisz trade
                    self.paper_trades.append({
                        'timestamp': datetime.now(),
                        'action': 'open',
                        'side': signal['side'],
                        'price': entry_price,
                        'size': position_size_usd,
                        'reason': signal['reason']
                    })
                    
                    # Log do CSV z dodatkowymi wskaźnikami
                    self.trade_logger.log_trade({
                        'timestamp': datetime.now().isoformat(),
                        'action': 'open',
                        'side': signal['side'],
                        'price': entry_price,
                        'size': position_size_usd,
                        'reason': signal['reason'],
                        'rsi_5': signal['indicators'].get('rsi_5', 0),
                        'rsi_7': signal['indicators'].get('rsi_7', 0),
                        'rsi_10': signal['indicators'].get('rsi_10', 0),
                        'vwap': signal['indicators'].get('vwap', 0),
                        'price_vs_vwap': signal['indicators'].get('price_vs_vwap', 0),
                        'volume_spike': signal['indicators'].get('volume_spike_500', False),
                        'trend': signal['indicators']['trend'],
                        'sentiment': signal['indicators'].get('sentiment', 'neutral'),
                        'order_book_imbalance': signal['indicators'].get('order_book_imbalance', 0),
                        'session': signal['indicators'].get('session', 'other'),
                        'high_liquidity': signal['indicators'].get('high_liquidity_hours', 0),
                        'balance_after': self.paper_balance
                    })
                    
                    # Telegram notification
                    self.telegram.notify_trade_opened(signal['side'], entry_price, position_size_usd, signal['reason'])
                
                self.trades_today += 1
                self.last_trade_time = time.time()
                
        except Exception as e:
            self.logger.error(f"Error opening position: {e}")
            self.telegram.notify_error(f"Error opening position: {e}")
    
    def close_position(self, position, reason="Manual close"):
        """Zamyka istniejącą pozycję"""
        try:
            side = 'sell' if position['side'] == 'long' else 'buy'
            amount = position['size']
            
            order = self.place_order(side, amount, reduce_only=True)
            
            if order:
                # Oblicz PnL
                if Config.PAPER_TRADING:
                    current_price = position['mark_price']
                    if position['side'] == 'long':
                        pnl = (current_price - position['entry_price']) * position['size']
                    else:
                        pnl = (position['entry_price'] - current_price) * position['size']
                    
                    position['unrealized_pnl'] = pnl
                    
                    # Zaktualizuj saldo
                    self.paper_balance += position['notional'] + pnl
                    
                    # Usuń pozycję
                    self.paper_positions.remove(position)
                    
                    # Zapisz trade
                    self.paper_trades.append({
                        'timestamp': datetime.now(),
                        'action': 'close',
                        'side': position['side'],
                        'price': current_price,
                        'size': position['notional'],
                        'pnl': pnl,
                        'reason': reason
                    })
                    
                    # Log do CSV
                    self.trade_logger.log_trade({
                        'timestamp': datetime.now().isoformat(),
                        'action': 'close',
                        'side': position['side'],
                        'price': current_price,
                        'size': position['notional'],
                        'pnl': pnl,
                        'reason': reason,
                        'balance_after': self.paper_balance
                    })
                    
                    # Telegram notification
                    self.telegram.notify_trade_closed(position['side'], position['entry_price'], current_price, pnl, reason)
                else:
                    pnl = position.get('unrealized_pnl', 0)
                
                self.daily_pnl += pnl
                
                self.logger.info(f"{'[PAPER] ' if Config.PAPER_TRADING else ''}Closed {position['side']} position. PnL: {pnl:.2f} USDT. Reason: {reason}")
                
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            self.telegram.notify_error(f"Error closing position: {e}")
    
    def update_paper_positions(self):
        """Aktualizuje ceny i PnL dla paper positions"""
        if not Config.PAPER_TRADING:
            return
        
        ticker = self.data_collector.get_ticker()
        if not ticker:
            return
        
        current_price = ticker['last']
        current_time = time.time()
        
        for position in self.paper_positions:
            position['mark_price'] = current_price
            
            # Oblicz unrealized PnL
            if position['side'] == 'long':
                position['unrealized_pnl'] = (current_price - position['entry_price']) * position['size']
            else:
                position['unrealized_pnl'] = (position['entry_price'] - current_price) * position['size']
            
            # Sprawdź czas trzymania dla scalping
            if position.get('scalp_trade') and (current_time - position['opened_at'].timestamp()) > Config.SCALPING_MAX_HOLD_TIME:
                self.close_position(position, "Scalping time limit exceeded")
    
    def manage_positions(self, signal_analysis=None):
        """Zarządza otwartymi pozycjami"""
        if Config.PAPER_TRADING:
            self.update_paper_positions()
        
        positions = self.get_positions()
        
        for position in positions[:]:  # Kopia listy do iteracji
            current_price = position['mark_price']
            entry_price = position['entry_price']
            
            # Dodatkowe warunki wyjścia dla skalpowania
            if position.get('scalp_trade'):
                pnl_percent = (position['unrealized_pnl'] / position['notional']) * 100
                
                # Szybkie wyjście dla skalpowania
                if pnl_percent >= Config.SCALPING_MIN_PROFIT_PERCENT:
                    self.close_position(position, "Scalping profit target reached")
                    continue
            
            if position['side'] == 'long':
                # Stop loss dla long
                if current_price <= entry_price * (1 - Config.STOP_LOSS_PERCENT/100):
                    self.close_position(position, "Stop loss hit")
                # Take profit dla long
                elif current_price >= entry_price * (1 + Config.TAKE_PROFIT_PERCENT/100):
                    self.close_position(position, "Take profit hit")
            
            elif position['side'] == 'short':
                # Stop loss dla short
                if current_price >= entry_price * (1 + Config.STOP_LOSS_PERCENT/100):
                    self.close_position(position, "Stop loss hit")
                # Take profit dla short
                elif current_price <= entry_price * (1 - Config.TAKE_PROFIT_PERCENT/100):
                    self.close_position(position, "Take profit hit")
    
    def run_trading_cycle(self):
        """Pojedynczy cykl tradingowy"""
        try:
            # Sprawdź limity ryzyka
            if not self.check_risk_limits():
                return
            
            # Pobierz dane
            df = self.data_collector.get_ohlcv_data(limit=100)
            
            if df is None or df.empty:
                return
            
            # Pobierz order book i ostatnie transakcje
            order_book = self.data_collector.get_order_book()
            recent_trades = self.data_collector.get_recent_trades()
            
            # Pobierz aktualne pozycje
            positions = self.get_positions()
            
            # Generuj sygnał z pełną analizą
            signal = self.strategy.generate_signal(
                df=df,
                existing_positions=positions,
                order_book=order_book,
                recent_trades=recent_trades
            )
            
            # Log aktualnego stanu
            ticker = self.data_collector.get_ticker()
            if ticker:
                self.logger.info(
                    f"BTC Price: {ticker['last']:.2f}, "
                    f"RSI_5: {signal['indicators'].get('rsi_5', 0):.2f}, "
                    f"RSI_7: {signal['indicators'].get('rsi_7', 0):.2f}, "
                    f"VWAP: {signal['indicators'].get('vwap', 0):.2f}, "
                    f"Vol Spike: {signal['indicators'].get('volume_spike_500', False)}, "
                    f"Trend: {signal['indicators']['trend']}, "
                    f"OB Imbalance: {signal['indicators'].get('order_book_imbalance', 0):.2f}"
                )
            
            # Zarządzaj pozycjami
            self.manage_positions(signal_analysis=signal)
            
            # Wykonaj akcję na podstawie sygnału
            if signal['action'] == 'OPEN' and signal['confidence'] >= 0.7:
                # Dodatkowe sprawdzenie dla skalpowania
                if signal.get('scalp_trade'):
                    current_time = time.time()
                    if current_time - self.last_trade_time < 60:  # Minimalna przerwa między tradami
                        self.logger.info("Scalping: Waiting for cooldown period")
                        return
                
                self.open_position(signal)
            elif signal['action'] == 'CLOSE':
                # Znajdź pozycję do zamknięcia
                for pos in positions:
                    if pos['side'] == signal['side']:
                        self.close_position(pos, signal['reason'])
            
            # Log statystyk
            if Config.PAPER_TRADING:
                self.logger.info(f"[PAPER] Balance: {self.paper_balance:.2f} USDT, Daily PnL: {self.daily_pnl:.2f} USDT, Trades: {self.trades_today}")
            else:
                self.logger.info(f"Daily PnL: {self.daily_pnl:.2f} USDT, Trades today: {self.trades_today}")
            
        except Exception as e:
            self.logger.error(f"Error in trading cycle: {e}")
            self.telegram.notify_error(f"Trading cycle error: {e}")
    
    def generate_daily_summary(self):
        """Generuje dzienne podsumowanie"""
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'trading_mode': 'PAPER' if Config.PAPER_TRADING else 'LIVE',
            'total_trades': self.trades_today,
            'daily_pnl': self.daily_pnl,
            'final_balance': self.paper_balance if Config.PAPER_TRADING else 'N/A',
            'positions': len(self.get_positions()),
            'runtime_hours': (datetime.now() - self.startup_time).total_seconds() / 3600
        }
        
        if Config.PAPER_TRADING and self.paper_trades:
            closed_trades = [t for t in self.paper_trades if t.get('action') == 'close']
            if closed_trades:
                winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
                summary['win_rate'] = len(winning_trades) / len(closed_trades) * 100
                summary['avg_win'] = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
                summary['avg_loss'] = sum(t.get('pnl', 0) for t in closed_trades if t.get('pnl', 0) < 0) / len([t for t in closed_trades if t.get('pnl', 0) < 0]) if any(t.get('pnl', 0) < 0 for t in closed_trades) else 0
        
        self.trade_logger.save_daily_summary(summary)
        return summary
    
    def start(self):
        """Uruchamia bota"""
        mode = "PAPER TRADING" if Config.PAPER_TRADING else "LIVE TRADING"
        self.logger.info(f"=== Enhanced Bitget Futures Trading Bot Started ({mode}) ===")
        self.logger.info(f"Trading pair: {Config.TRADING_SYMBOL}")
        self.logger.info(f"Leverage: {Config.LEVERAGE}x")
        self.logger.info(f"Check interval: {Config.CHECK_INTERVAL} seconds")
        self.logger.info(f"Scalping Enabled: {Config.SCALPING_ENABLED}")
        
        # Notify Telegram about bot start
        self.telegram.notify_bot_start()
        
        try:
            while True:
                try:
                    self.run_trading_cycle()
                    time.sleep(Config.CHECK_INTERVAL)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.logger.error(f"Error in trading cycle: {e}")
                    time.sleep(60)
        
        except KeyboardInterrupt:
            self.logger.info("\n=== Bot stopped by user ===")
            summary = self.generate_daily_summary()
            
            if Config.PAPER_TRADING and self.paper_trades:
                self.logger.info(f"[PAPER] Final balance: {self.paper_balance:.2f} USDT")
                self.logger.info(f"[PAPER] Total trades: {len(self.paper_trades)}")
                self.logger.info(f"[PAPER] Final PnL: {self.paper_balance - 1000:.2f} USDT")
                
                if 'win_rate' in summary:
                    self.logger.info(f"[PAPER] Win rate: {summary['win_rate']:.2f}%")
            
            # Notify Telegram about bot stop and daily summary
            self.telegram.notify_bot_stop()
            if summary.get('total_trades', 0) > 0:
                self.telegram.notify_daily_summary(summary)
            
            self.logger.info("=== Trading session ended ===")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self.telegram.notify_error(f"Bot crashed: {e}")
            self.logger.info("Bot stopped due to error")