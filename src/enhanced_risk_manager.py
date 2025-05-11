# src/enhanced_risk_manager.py
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config.settings import Config


class EnhancedRiskManager:
    """Advanced risk management with dynamic leverage and sophisticated position sizing."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.trade_history = []
        self.consecutive_losses = 0
        self.daily_starting_balance = 0
        self.daily_pnl = 0
        self.system_paused = False
        self.pause_until = None
        self.leverage_multiplier = 1.0
        
        # Advanced metrics
        self.volatility_history = []
        self.signal_accuracy = {}
        self.risk_metrics = {
            'current_exposure': 0,
            'max_exposure': 0,
            'realized_pnl': 0,
            'unrealized_pnl': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0
        }
    
    def set_daily_starting_balance(self, balance: float):
        """Set starting balance for daily calculations."""
        self.daily_starting_balance = balance
        self.daily_pnl = 0
    
    def calculate_dynamic_leverage(self, symbol: str, market_data: Dict, 
                                 signal_strength: float) -> int:
        """Calculate dynamic leverage based on volatility and signal strength."""
        try:
            # Get volatility from ATR
            atr_percent = market_data.get('timeframes', {}).get('1m', {}).get(
                'indicators', {}).get('atr_percent', 0)
            
            # Base leverage calculation
            if atr_percent <= 0.5:  # Very low volatility
                base_leverage = 20
            elif atr_percent <= 1.0:  # Low volatility
                base_leverage = 15
            elif atr_percent <= 1.5:  # Medium volatility
                base_leverage = 10
            elif atr_percent <= 2.0:  # High volatility
                base_leverage = 7
            else:  # Very high volatility
                base_leverage = 5
            
            # Adjust based on signal strength
            signal_multiplier = 1.0
            if signal_strength >= 90:
                signal_multiplier = 1.3
            elif signal_strength >= 80:
                signal_multiplier = 1.1
            elif signal_strength < 60:
                signal_multiplier = 0.7
            
            # Apply system-wide leverage multiplier (penalties)
            final_leverage = int(base_leverage * signal_multiplier * self.leverage_multiplier)
            
            # Apply limits
            final_leverage = max(Config.MIN_LEVERAGE, min(Config.MAX_LEVERAGE, final_leverage))
            
            self.logger.info(
                f"Dynamic leverage for {symbol}: {final_leverage}x "
                f"(volatility: {atr_percent:.2f}%, strength: {signal_strength:.1f})"
            )
            
            return final_leverage
            
        except Exception as e:
            self.logger.error(f"Error calculating dynamic leverage: {e}")
            return Config.BASE_LEVERAGE  # Fallback to default
    
    def calculate_position_size(self, balance: float, current_price: float,
                              signal_strength: float, leverage: int, atr: float) -> float:
        """Calculate position size based on signal confidence and risk limits."""
        try:
            # Calculate max risk amount
            max_risk_amount = balance * Config.MAX_RISK_PER_TRADE
            
            # Apply signal strength scaling
            confidence_multiplier = self._get_confidence_multiplier(signal_strength)
            risk_amount = max_risk_amount * confidence_multiplier
            
            # Calculate position size based on risk and stop loss distance
            stop_distance = atr * Config.STOP_LOSS_ATR_MULTIPLIER
            position_size_btc = risk_amount / stop_distance
            position_size_usd = position_size_btc * current_price
            
            # Apply leverage
            leveraged_position_size = position_size_usd * leverage
            
            # Check against account limits
            max_position = min(
                balance * Config.MAX_POSITION_SIZE_PERCENT,  # Max % of balance per position
                leveraged_position_size
            )
            
            # Apply daily loss limit check
            if not self._check_daily_loss_limit():
                self.logger.warning("Daily loss limit reached - reducing position size")
                max_position *= 0.3  # Reduce to 30% if approaching limit
            
            # Ensure minimum trade size
            if max_position < Config.MIN_POSITION_SIZE_USD:
                return 0
            
            return max_position
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0
    
    def _get_confidence_multiplier(self, signal_strength: float) -> float:
        """Convert signal strength to position size multiplier."""
        if signal_strength >= 90:
            return 1.0
        elif signal_strength >= 80:
            return 0.8
        elif signal_strength >= 70:
            return 0.6
        else:
            return 0.4
    
    def check_trading_allowed(self) -> Dict[str, bool]:
        """Comprehensive check if trading is allowed."""
        checks = {
            'system_active': not self.system_paused,
            'daily_loss_ok': self._check_daily_loss_limit(),
            'consecutive_losses_ok': self.consecutive_losses < Config.MAX_CONSECUTIVE_LOSSES,
            'max_positions_ok': self._check_position_limit(),
            'pause_expired': self._check_pause_expired()
        }
        
        checks['trading_allowed'] = all(checks.values())
        
        if not checks['trading_allowed']:
            reasons = [k for k, v in checks.items() if not v]
            self.logger.warning(f"Trading blocked: {', '.join(reasons)}")
        
        return checks
    
    def _check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit is exceeded."""
        if self.daily_starting_balance <= 0:
            return True
            
        daily_loss_percent = abs(self.daily_pnl / self.daily_starting_balance) * 100
        max_daily_loss_percent = Config.MAX_DAILY_LOSS_PERCENT
        
        return daily_loss_percent < max_daily_loss_percent
    
    def _check_position_limit(self) -> bool:
        """Check if max positions limit is reached."""
        # This should be checked against actual open positions
        # For now, return True as placeholder
        return True
    
    def _check_pause_expired(self) -> bool:
        """Check if system pause has expired."""
        if self.pause_until is None:
            return True
        
        if datetime.now() >= self.pause_until:
            self.system_paused = False
            self.pause_until = None
            self.logger.info("System pause expired - trading resumed")
            return True
            
        return False
    
    def record_trade(self, trade: Dict):
        """Record trade and update risk metrics."""
        self.trade_history.append(trade)
        
        if trade.get('action') == 'close' and 'pnl' in trade:
            pnl = trade['pnl']
            self.daily_pnl += pnl
            
            # Update consecutive losses
            if pnl < 0:
                self.consecutive_losses += 1
                
                # Check for system pause conditions
                if self.consecutive_losses >= Config.MAX_CONSECUTIVE_LOSSES:
                    self._apply_system_pause()
            else:
                self.consecutive_losses = 0  # Reset on win
            
            # Update risk metrics
            self._update_risk_metrics(trade)
    
    def _apply_system_pause(self):
        """Apply system pause due to consecutive losses."""
        self.system_paused = True
        self.pause_until = datetime.now() + timedelta(minutes=Config.SYSTEM_PAUSE_MINUTES)
        
        self.logger.warning(
            f"System paused due to {self.consecutive_losses} consecutive losses. "
            f"Trading will resume at {self.pause_until}"
        )
    
    def _update_risk_metrics(self, trade: Dict):
        """Update comprehensive risk metrics."""
        # Update realized PnL
        self.risk_metrics['realized_pnl'] += trade.get('pnl', 0)
        
        # Calculate win rate
        closed_trades = [t for t in self.trade_history if t.get('action') == 'close']
        if closed_trades:
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            self.risk_metrics['win_rate'] = len(winning_trades) / len(closed_trades)
        
        # Update signal accuracy for the strategy
        strategy = trade.get('reason', 'unknown')
        if strategy not in self.signal_accuracy:
            self.signal_accuracy[strategy] = {'wins': 0, 'losses': 0}
        
        if trade.get('pnl', 0) > 0:
            self.signal_accuracy[strategy]['wins'] += 1
        else:
            self.signal_accuracy[strategy]['losses'] += 1
    
    def apply_adaptive_risk_adjustment(self):
        """Adjust risk parameters based on recent performance."""
        recent_trades = self.trade_history[-Config.PERFORMANCE_LOOKBACK:]  # Last N trades
        
        if len(recent_trades) >= 5:
            recent_pnl = sum(t.get('pnl', 0) for t in recent_trades)
            
            if recent_pnl < 0:
                # Reduce leverage if recent performance is poor
                self.leverage_multiplier = max(Config.MIN_LEVERAGE_MULTIPLIER, 
                                             self.leverage_multiplier * Config.LEVERAGE_REDUCTION_FACTOR)
                self.logger.info(f"Reduced leverage multiplier to {self.leverage_multiplier}")
            else:
                # Gradually increase leverage if performing well
                self.leverage_multiplier = min(Config.MAX_LEVERAGE_MULTIPLIER, 
                                             self.leverage_multiplier * Config.LEVERAGE_INCREASE_FACTOR)
    
    def calculate_stop_loss(self, entry_price: float, side: str, atr: float,
                          signal_strength: float = 70) -> float:
        """Calculate dynamic stop loss based on ATR and signal strength."""
        # Base stop distance
        if signal_strength >= 80:
            stop_multiplier = Config.TIGHT_STOP_MULTIPLIER  # Tighter stop for strong signals
        else:
            stop_multiplier = Config.WIDE_STOP_MULTIPLIER  # Wider stop for weaker signals
        
        stop_distance = atr * stop_multiplier
        
        if side == 'long':
            return entry_price * (1 - stop_distance)
        else:  # short
            return entry_price * (1 + stop_distance)
    
    def get_risk_report(self) -> Dict:
        """Generate comprehensive risk report."""
        return {
            'daily_pnl': self.daily_pnl,
            'daily_pnl_percent': (self.daily_pnl / self.daily_starting_balance * 100) 
                               if self.daily_starting_balance > 0 else 0,
            'consecutive_losses': self.consecutive_losses,
            'system_paused': self.system_paused,
            'pause_until': self.pause_until.isoformat() if self.pause_until else None,
            'leverage_multiplier': self.leverage_multiplier,
            'risk_metrics': self.risk_metrics,
            'signal_accuracy': self.signal_accuracy,
            'total_trades': len(self.trade_history),
            'active_strategies': list(self.signal_accuracy.keys())
        }