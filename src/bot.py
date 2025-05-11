# src/bot.py
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from config.settings import Config
from src.exchange import ExchangeConnector
from src.strategy import TradingStrategy
from src.market_analyzer import MarketAnalyzer
from src.logger import TradeLogger
from src.notifier import TelegramNotifier


class TradingBot:
    """Main trading bot class."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.exchange = ExchangeConnector()
        self.strategy = TradingStrategy()
        self.market_analyzer = MarketAnalyzer()
        self.trade_logger = TradeLogger()
        self.notifier = TelegramNotifier()
        
        # State management
        self.positions = []
        self.daily_pnl = 0.0
        self.trades_today = 0
        
        # Paper trading state
        if Config.PAPER_TRADING:
            self.paper_balance = 1000.0
            self.paper_positions = []
        
        self._initialize()
    
    def _initialize(self):
        """Initialize bot components."""
        try:
            # Set leverage
            self.exchange.set_leverage(Config.TRADING_SYMBOL, Config.LEVERAGE)
            
            # Check balance
            balance = self.exchange.get_balance()
            if balance:
                self.logger.info(f"Account balance: {balance['available']:.2f} USDT")
            
            # Check existing positions
            self.positions = self.exchange.get_positions()
            if self.positions:
                self.logger.info(f"Found {len(self.positions)} open positions")
            
            # Send startup notification
            self.notifier.notify_startup()
            
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise
    
    def run(self):
        """Main bot loop."""
        self.logger.info("Bot started successfully")
        
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
        """Execute single trading cycle."""
        # Check risk limits
        if not self._check_risk_limits():
            return
        
        # Get market data
        market_data = self._get_market_data()
        if not market_data:
            return
        
        # Analyze market
        analysis = self.market_analyzer.analyze(market_data)
        
        # Generate trading signal
        signal = self.strategy.generate_signal(market_data, analysis, self.positions)
        
        # Log current state
        self._log_market_state(market_data, analysis)
        
        # Execute trading logic
        self._execute_trading_logic(signal)
        
        # Manage existing positions
        self._manage_positions()
    
    def _get_market_data(self) -> Optional[Dict]:
        """Fetch comprehensive market data."""
        try:
            # Get OHLCV data
            ohlcv = self.exchange.get_ohlcv(limit=100)
            if ohlcv is None or ohlcv.empty:
                return None
            
            # Get additional market data
            ticker = self.exchange.get_ticker()
            order_book = self.exchange.get_order_book()
            recent_trades = self.exchange.get_recent_trades()
            
            return {
                'ohlcv': ohlcv,
                'ticker': ticker,
                'order_book': order_book,
                'recent_trades': recent_trades
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching market data: {e}")
            return None
    
    def _execute_trading_logic(self, signal: Dict):
        """Execute trading based on signal."""
        if signal['action'] == 'OPEN' and signal['confidence'] >= 0.7:
            self._open_position(signal)
        elif signal['action'] == 'CLOSE':
            self._close_position(signal)
    
    def _open_position(self, signal: Dict):
        """Open new position."""
        try:
            # Calculate position size
            balance = self._get_available_balance()
            if balance <= 0:
                return
            
            position_size_usd = min(Config.TRADE_AMOUNT_USDT, balance * 0.95)
            position_size_btc = position_size_usd / signal['entry_price']
            
            # Place order
            order = self.exchange.place_order(
                side=signal['side'],
                amount=position_size_btc,
                order_type='market'
            )
            
            if order:
                position = {
                    'id': order['id'],
                    'side': signal['side'],
                    'entry_price': signal['entry_price'],
                    'size': position_size_btc,
                    'size_usd': position_size_usd,
                    'opened_at': datetime.now(),
                    'stop_loss': signal.get('stop_loss'),
                    'take_profit': signal.get('take_profit'),
                    'reason': signal['reason']
                }
                
                if Config.PAPER_TRADING:
                    self.paper_positions.append(position)
                    self.paper_balance -= position_size_usd
                else:
                    self.positions.append(position)
                
                self.trades_today += 1
                
                # Log trade
                self.trade_logger.log_trade({
                    'action': 'open',
                    'side': signal['side'],
                    'price': signal['entry_price'],
                    'size': position_size_usd,
                    'reason': signal['reason']
                })
                
                # Notify
                self.notifier.notify_trade_opened(
                    signal['side'],
                    signal['entry_price'],
                    position_size_usd,
                    signal['reason']
                )
                
                self.logger.info(f"Opened {signal['side']} position: {position_size_usd:.2f} USDT")
                
        except Exception as e:
            self.logger.error(f"Error opening position: {e}")
    
    def _close_position(self, signal: Dict):
        """Close existing position."""
        # Find matching position
        positions = self.paper_positions if Config.PAPER_TRADING else self.positions
        
        for position in positions:
            if position['side'] == signal['side']:
                self._execute_close(position, signal['reason'])
                break
    
    def _execute_close(self, position: Dict, reason: str):
        """Execute position close."""
        try:
            side = 'sell' if position['side'] == 'long' else 'buy'
            
            # Place closing order
            order = self.exchange.place_order(
                side=side,
                amount=position['size'],
                order_type='market',
                reduce_only=True
            )
            
            if order:
                # Calculate PnL
                current_price = order.get('price', position['entry_price'])
                pnl = self._calculate_pnl(position, current_price)
                
                # Update state
                if Config.PAPER_TRADING:
                    self.paper_balance += position['size_usd'] + pnl
                    self.paper_positions.remove(position)
                else:
                    self.positions.remove(position)
                
                self.daily_pnl += pnl
                
                # Log trade
                self.trade_logger.log_trade({
                    'action': 'close',
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'size': position['size_usd'],
                    'pnl': pnl,
                    'reason': reason
                })
                
                # Notify
                self.notifier.notify_trade_closed(
                    position['side'],
                    position['entry_price'],
                    current_price,
                    pnl,
                    reason
                )
                
                self.logger.info(f"Closed {position['side']} position. PnL: {pnl:.2f} USDT")
                
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
    
    def _manage_positions(self):
        """Manage existing positions (stop loss, take profit)."""
        positions = self.paper_positions if Config.PAPER_TRADING else self.positions
        
        for position in positions[:]:  # Copy list for iteration
            try:
                ticker = self.exchange.get_ticker()
                if not ticker:
                    continue
                
                current_price = ticker['last']
                
                # Check stop loss and take profit
                if self._should_close_position(position, current_price):
                    self._execute_close(position, "Risk management")
                    
            except Exception as e:
                self.logger.error(f"Error managing position: {e}")
    
    def _should_close_position(self, position: Dict, current_price: float) -> bool:
        """Check if position should be closed."""
        if position['side'] == 'long':
            # Stop loss
            if current_price <= position['entry_price'] * (1 - Config.STOP_LOSS_PERCENT/100):
                return True
            # Take profit
            if current_price >= position['entry_price'] * (1 + Config.TAKE_PROFIT_PERCENT/100):
                return True
        else:  # short
            # Stop loss
            if current_price >= position['entry_price'] * (1 + Config.STOP_LOSS_PERCENT/100):
                return True
            # Take profit
            if current_price <= position['entry_price'] * (1 - Config.TAKE_PROFIT_PERCENT/100):
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
    
    def _check_risk_limits(self) -> bool:
        """Check if trading is allowed based on risk limits."""
        # Daily loss limit
        if self.daily_pnl <= -Config.MAX_DAILY_LOSS:
            self.logger.warning(f"Daily loss limit reached: {self.daily_pnl:.2f} USDT")
            return False
        
        # Position limit
        positions = self.paper_positions if Config.PAPER_TRADING else self.positions
        if len(positions) >= Config.MAX_OPEN_POSITIONS:
            self.logger.info(f"Maximum positions reached: {len(positions)}")
            return False
        
        return True
    
    def _get_available_balance(self) -> float:
        """Get available balance for trading."""
        if Config.PAPER_TRADING:
            return self.paper_balance
        else:
            balance = self.exchange.get_balance()
            return balance['available'] if balance else 0
    
    def _log_market_state(self, market_data: Dict, analysis: Dict):
        """Log current market state."""
        if market_data.get('ticker'):
            ticker = market_data['ticker']
            self.logger.info(
                f"BTC Price: {ticker['last']:.2f}, "
                f"RSI: {analysis.get('rsi', 0):.2f}, "
                f"Volume Spike: {analysis.get('volume_spike', False)}, "
                f"Trend: {analysis.get('trend', 'unknown')}"
            )
    
    def _shutdown(self):
        """Cleanup on shutdown."""
        # Generate daily summary
        summary = self.trade_logger.generate_daily_summary({
            'trades_today': self.trades_today,
            'daily_pnl': self.daily_pnl,
            'final_balance': self._get_available_balance()
        })
        
        # Send notifications
        self.notifier.notify_shutdown()
        if summary:
            self.notifier.notify_daily_summary(summary)
        
        self.logger.info("Bot shutdown complete")