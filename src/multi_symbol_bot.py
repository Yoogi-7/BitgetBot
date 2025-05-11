# src/multi_symbol_bot.py
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from config.settings import Config
from src.exchange import ExchangeConnector
from src.data_collector import EnhancedDataCollector
from src.strategy import TradingStrategy
from src.enhanced_strategy import EnhancedTradingStrategy
from src.market_analyzer import MarketAnalyzer
from src.logger import TradeLogger
from src.notifier import TelegramNotifier
from src.risk_manager import RiskManager
from src.security_filters import SecurityFilters
from src.kpi_tracker import KPITracker
from src.dynamic_filter import DynamicFilter
from src.signal_strength import SignalStrengthCalculator
from src.sentiment_analyzer import EnhancedSentimentAnalyzer


class MultiSymbolTradingBot:
    """Enhanced trading bot with multi-symbol support."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.exchange = ExchangeConnector()
        self.data_collector = EnhancedDataCollector()
        self.strategy = TradingStrategy()
        self.enhanced_strategy = EnhancedTradingStrategy()
        self.market_analyzer = MarketAnalyzer()
        self.trade_logger = TradeLogger()
        self.notifier = TelegramNotifier()
        self.risk_manager = RiskManager()
        self.security_filters = SecurityFilters()
        self.kpi_tracker = KPITracker()
        self.dynamic_filter = DynamicFilter()
        self.signal_strength_calculator = SignalStrengthCalculator()
        self.sentiment_analyzer = EnhancedSentimentAnalyzer()
        
        # State management
        self.positions_by_symbol = {}
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.daily_starting_balance = 0.0
        
        # Paper trading state
        if Config.PAPER_TRADING:
            self.paper_balance = 1000.0
            self.paper_positions_by_symbol = {}
            self.daily_starting_balance = self.paper_balance
        
        # Symbol tracking
        self.active_symbols = []
        self.symbol_metrics = {}
        
        self._initialize()
    
    def _initialize(self):
        """Initialize bot components."""
        try:
            # Initialize for each symbol
            for symbol in Config.TRADING_SYMBOLS:
                # Set leverage for each symbol
                self.exchange.set_leverage(symbol, Config.LEVERAGE)
                
                # Initialize position tracking
                self.positions_by_symbol[symbol] = []
                if Config.PAPER_TRADING:
                    self.paper_positions_by_symbol[symbol] = []
            
            # Check balance
            balance = self.exchange.get_balance()
            if balance:
                self.logger.info(f"Account balance: {balance['available']:.2f} USDT")
                if not Config.PAPER_TRADING:
                    self.daily_starting_balance = balance['available']
            
            # Send startup notification
            self.notifier.notify_startup()
            
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise
    
    def run(self):
        """Main bot loop."""
        self.logger.info("Multi-Symbol Trading Bot started successfully")
        
        while True:
            try:
                self._trading_cycle()
                time.sleep(Config.CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                self.logger.info("Bot stopped by user")
                self._shutdown()
                break
            except Exception as e:
                self.logger.error(f"Error in trading cycle: {e}")
                self.notifier.notify_error(str(e))
                time.sleep(60)  # Wait before retry
    
    def _trading_cycle(self):
        """Execute single trading cycle for all symbols."""
        # Check daily drawdown limit
        current_balance = self._get_available_balance()
        if not self.kpi_tracker.check_daily_drawdown(current_balance, self.daily_starting_balance):
        # Check daily drawdown limit
        current_balance = self._get_available_balance()
        if not self.kpi_tracker.check_daily_drawdown(current_balance, self.daily_starting_balance):
            self.logger.warning("Daily drawdown limit reached - pausing trading")
            return
        
        # Get market data for all symbols
        market_data_all = {}
        for symbol in Config.TRADING_SYMBOLS:
            data = self.data_collector.collect_comprehensive_data(symbol)
            if data:
                market_data_all[symbol] = data
        
        # Filter symbols based on volatility, volume, and liquidity
        self.active_symbols = self.dynamic_filter.filter_symbols(market_data_all)
        
        if not self.active_symbols:
            self.logger.info("No symbols pass filtering criteria")
            return
        
        # Get sentiment analysis
        sentiment = self.sentiment_analyzer.get_comprehensive_sentiment()
        
        # Analyze each active symbol
        signals_by_symbol = {}
        
        for symbol in self.active_symbols:
            try:
                signal = self._analyze_symbol(symbol, market_data_all[symbol], sentiment)
                if signal and signal['strength']['total_score'] >= Config.MIN_SIGNAL_STRENGTH:
                    signals_by_symbol[symbol] = signal
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}")
        
        # Sort signals by strength
        sorted_signals = sorted(
            signals_by_symbol.items(), 
            key=lambda x: x[1]['strength']['total_score'], 
            reverse=True
        )
        
        # Execute trades for top signals
        self._execute_top_signals(sorted_signals, market_data_all)
        
        # Manage existing positions
        self._manage_all_positions()
        
        # Log summary
        self._log_cycle_summary(signals_by_symbol)
    
    def _analyze_symbol(self, symbol: str, market_data: Dict, sentiment: Dict) -> Optional[Dict]:
        """Analyze single symbol for trading opportunities."""
        # Check for market anomalies
        anomaly_check = self.security_filters.check_market_anomaly(market_data)
        if anomaly_check['is_anomaly'] and anomaly_check['recommendation'] == 'block_signal':
            self.logger.warning(f"{symbol}: Market anomaly detected - blocking signals")
            return None
        
        # Get positions for this symbol
        positions = self._get_positions_for_symbol(symbol)
        
        # Check if max positions reached for this symbol
        if len(positions) >= Config.MAX_POSITIONS_PER_SYMBOL:
            return None
        
        # Generate trading signal using enhanced strategy
        signal = self.enhanced_strategy.generate_signal(market_data, positions)
        
        if signal and signal.get('action') == 'OPEN':
            # Calculate signal strength
            strength = self.signal_strength_calculator.calculate_signal_strength(
                signal.get('indicators', {}),
                market_data,
                sentiment
            )
            
            signal['strength'] = strength
            signal['symbol'] = symbol
            
            # Check sentiment alignment
            if Config.SENTIMENT_ALIGNMENT_REQUIRED and not strength['sentiment_aligned']:
                self.logger.info(f"{symbol}: Signal rejected due to sentiment misalignment")
                return None
            
            # Check if signal is strong enough
            if strength['total_score'] < Config.MIN_SIGNAL_STRENGTH:
                self.logger.info(f"{symbol}: Signal too weak ({strength['total_score']:.1f})")
                return None
            
            return signal
        
        return None
    
    def _execute_top_signals(self, sorted_signals: List[Tuple[str, Dict]], 
                           market_data_all: Dict):
        """Execute trades for top-ranked signals."""
        # Check global position limits
        total_positions = sum(len(positions) for positions in self.positions_by_symbol.values())
        
        for symbol, signal in sorted_signals:
            if total_positions >= Config.MAX_TOTAL_POSITIONS:
                break
            
            # Check if strategy is allowed by risk manager
            if not self.risk_manager.is_strategy_allowed(signal.get('reason', '')):
                self.logger.warning(f"{symbol}: Strategy '{signal['reason']}' is temporarily excluded")
                continue
            
            # Ensure ethical trading
            if not self.security_filters.ensure_ethical_trading(signal):
                self.logger.warning(f"{symbol}: Signal blocked for ethical reasons")
                continue
            
            # Execute trade
            if self._open_position(symbol, signal, market_data_all[symbol]):
                total_positions += 1
    
    def _open_position(self, symbol: str, signal: Dict, market_data: Dict) -> bool:
        """Open position for specific symbol."""
        try:
            # Get available balance
            balance = self._get_available_balance()
            if balance <= 0:
                return False
            
            # Calculate position allocation
            allocated_balance = self._calculate_symbol_allocation(symbol, balance, signal)
            
            # Calculate position size based on ATR and risk
            atr = signal.get('atr', 0.02 * signal['entry_price'])
            position_size_usd = self.risk_manager.calculate_position_size(
                allocated_balance, signal['entry_price'], atr
            )
            
            if position_size_usd < 10:  # Minimum trade size
                self.logger.warning(f"{symbol}: Position size too small after risk adjustment")
                return False
            
            position_size = position_size_usd / signal['entry_price']
            
            # Place order
            order = self.exchange.place_order(
                side='buy' if signal['side'] == 'long' else 'sell',
                amount=position_size,
                order_type='market',
                symbol=symbol
            )
            
            if order:
                position = {
                    'id': order['id'],
                    'symbol': symbol,
                    'side': signal['side'],
                    'entry_price': signal['entry_price'],
                    'entry_time': datetime.now(),
                    'size': position_size,
                    'size_usd': position_size_usd,
                    'opened_at': datetime.now(),
                    'stop_loss': signal.get('stop_loss'),
                    'take_profit': signal.get('take_profit'),
                    'exit_time': signal.get('exit_time'),
                    'reason': signal['reason'],
                    'signal_strength': signal['strength']['total_score'],
                    'atr': atr
                }
                
                # Add position to tracking
                if Config.PAPER_TRADING:
                    self.paper_positions_by_symbol[symbol].append(position)
                    self.paper_balance -= position_size_usd
                else:
                    self.positions_by_symbol[symbol].append(position)
                
                self.trades_today += 1
                
                # Log trade
                trade_data = {
                    'action': 'open',
                    'symbol': symbol,
                    'side': signal['side'],
                    'price': signal['entry_price'],
                    'size': position_size_usd,
                    'reason': signal['reason'],
                    'signal_strength': signal['strength']['total_score'],
                    'sentiment_aligned': signal['strength']['sentiment_aligned']
                }
                self.trade_logger.log_trade(trade_data)
                
                # Notify
                self.notifier.notify_trade_opened(
                    signal['side'],
                    signal['entry_price'],
                    position_size_usd,
                    f"{symbol}: {signal['reason']} (Strength: {signal['strength']['total_score']:.1f})"
                )
                
                self.logger.info(
                    f"Opened {signal['side']} position on {symbol}: "
                    f"{position_size_usd:.2f} USDT (Signal strength: {signal['strength']['total_score']:.1f})"
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error opening position for {symbol}: {e}")
            return False
    
    def _calculate_symbol_allocation(self, symbol: str, balance: float, signal: Dict) -> float:
        """Calculate how much balance to allocate to this symbol."""
        if Config.SYMBOL_ALLOCATION_MODE == 'equal':
            # Equal allocation among all symbols
            return balance / len(Config.TRADING_SYMBOLS)
        
        elif Config.SYMBOL_ALLOCATION_MODE == 'volatility_weighted':
            # Allocate more to higher volatility symbols
            # TODO: Implement volatility-based allocation
            return balance / len(Config.TRADING_SYMBOLS)
        
        elif Config.SYMBOL_ALLOCATION_MODE == 'strength_weighted':
            # Allocate more to stronger signals
            strength = signal['strength']['total_score']
            weight = strength / 100.0
            return balance * weight * (1 / len(Config.TRADING_SYMBOLS))
        
        else:
            return balance / len(Config.TRADING_SYMBOLS)
    
    def _manage_all_positions(self):
        """Manage positions for all symbols."""
        for symbol in self.positions_by_symbol:
            self._manage_positions_for_symbol(symbol)
    
    def _manage_positions_for_symbol(self, symbol: str):
        """Manage positions for specific symbol."""
        positions = self._get_positions_for_symbol(symbol)
        
        for position in positions[:]:  # Copy list for iteration
            try:
                ticker = self.exchange.get_ticker(symbol)
                if not ticker:
                    continue
                
                current_price = ticker['last']
                
                # Check stop loss and take profit
                if self._should_close_position(position, current_price):
                    self._execute_close(position, "Risk management trigger")
                    
                # Check time-based exit
                elif position.get('exit_time') and datetime.now() >= position['exit_time']:
                    self._execute_close(position, "Time-based exit")
                    
            except Exception as e:
                self.logger.error(f"Error managing position for {symbol}: {e}")
    
    def _get_positions_for_symbol(self, symbol: str) -> List[Dict]:
        """Get positions for specific symbol."""
        if Config.PAPER_TRADING:
            return self.paper_positions_by_symbol.get(symbol, [])
        else:
            return self.positions_by_symbol.get(symbol, [])
    
    def _log_cycle_summary(self, signals_by_symbol: Dict):
        """Log summary of the trading cycle."""
        filter_summary = self.dynamic_filter.get_filter_summary()
        
        self.logger.info(
            f"Cycle summary - Active symbols: {len(self.active_symbols)}, "
            f"Filtered: {filter_summary['filtered_count']}, "
            f"Signals generated: {len(signals_by_symbol)}"
        )
        
        if signals_by_symbol:
            top_signals = sorted(
                signals_by_symbol.items(),
                key=lambda x: x[1]['strength']['total_score'],
                reverse=True
            )[:3]
            
            self.logger.info("Top 3 signals:")
            for symbol, signal in top_signals:
                self.logger.info(
                    f"  {symbol}: {signal['side']} - "
                    f"Strength: {signal['strength']['total_score']:.1f}, "
                    f"Sentiment aligned: {signal['strength']['sentiment_aligned']}"
                )
    
    def _execute_close(self, position: Dict, reason: str):
        """Execute position close with risk tracking."""
        try:
            symbol = position['symbol']
            side = 'sell' if position['side'] == 'long' else 'buy'
            
            # Place closing order
            order = self.exchange.place_order(
                side=side,
                amount=position['size'],
                order_type='market',
                reduce_only=True,
                symbol=symbol
            )
            
            if order:
                # Calculate PnL
                current_price = order.get('price', position['entry_price'])
                pnl = self._calculate_pnl(position, current_price)
                pnl_percent = (pnl / position['size_usd']) * 100
                
                # Update state
                if Config.PAPER_TRADING:
                    self.paper_balance += position['size_usd'] + pnl
                    self.paper_positions_by_symbol[symbol].remove(position)
                else:
                    self.positions_by_symbol[symbol].remove(position)
                
                self.daily_pnl += pnl
                
                # Log trade
                trade_data = {
                    'action': 'close',
                    'symbol': symbol,
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'size': position['size_usd'],
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'reason': reason,
                    'signal_strength': position.get('signal_strength', 0)
                }
                self.trade_logger.log_trade(trade_data)
                self.risk_manager.record_trade(trade_data)
                self.kpi_tracker.track_trade_kpi(trade_data)
                
                # Notify
                self.notifier.notify_trade_closed(
                    position['side'],
                    position['entry_price'],
                    current_price,
                    pnl,
                    f"{symbol}: {reason}"
                )
                
                self.logger.info(
                    f"Closed {position['side']} position on {symbol}. "
                    f"PnL: {pnl:.2f} USDT ({pnl_percent:.2f}%)"
                )
                
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
    
    def _should_close_position(self, position: Dict, current_price: float) -> bool:
        """Check if position should be closed based on risk management."""
        # Check custom stop loss
        if position.get('stop_loss'):
            if position['side'] == 'long' and current_price <= position['stop_loss']:
                return True
            elif position['side'] == 'short' and current_price >= position['stop_loss']:
                return True
        
        # Check take profit
        if position.get('take_profit'):
            if position['side'] == 'long' and current_price >= position['take_profit']:
                return True
            elif position['side'] == 'short' and current_price <= position['take_profit']:
                return True
        
        # Scalping time limit
        if Config.SCALPING_ENABLED and position.get('opened_at'):
            hold_time = (datetime.now() - position['opened_at']).total_seconds()
            if hold_time > Config.SCALPING_MAX_HOLD_TIME:
                return True
        
        return False
    
    def _calculate_pnl(self, position: Dict, current_price: float) -> float:
        """Calculate position PnL."""
        if position['side'] == 'long':
            return (current_price - position['entry_price']) * position['size']
        else:
            return (position['entry_price'] - current_price) * position['size']
    
    def _get_available_balance(self) -> float:
        """Get available balance for trading."""
        if Config.PAPER_TRADING:
            return self.paper_balance
        else:
            balance = self.exchange.get_balance()
            return balance['available'] if balance else 0
    
    def _shutdown(self):
        """Cleanup on shutdown."""
        # Generate report
        kpi_report_file = self.kpi_tracker.export_kpi_report()
        
        # Generate summary
        summary = {
            'trades_today': self.trades_today,
            'daily_pnl': self.daily_pnl,
            'final_balance': self._get_available_balance(),
            'symbols_traded': list(self.symbol_metrics.keys()),
            'filter_summary': self.dynamic_filter.get_filter_summary()
        }
        
        self.notifier.notify_shutdown()
        self.logger.info(f"Multi-Symbol Bot shutdown complete")