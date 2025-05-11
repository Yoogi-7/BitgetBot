# src/risk_manager.py
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config.settings import Config


class RiskManager:
    """Advanced risk management with penalties and exclusions."""
    
    def __init__(self):
        self.trade_history = []
        self.penalty_multiplier = 1.0
        self.excluded_strategies = {}  # strategy -> exclusion_end_time
        self.last_big_loss_time = None
    
    def calculate_position_size(self, balance: float, current_price: float, 
                              atr: float) -> float:
        """Calculate position size based on ATR and account risk."""
        # Podstawowy rozmiar pozycji
        risk_amount = balance * Config.RISK_PER_TRADE
        
        # Oblicz stop loss distance na podstawie ATR
        stop_distance = atr * 2  # 2× ATR dla stop loss
        
        # Oblicz wielkość pozycji
        position_size_btc = risk_amount / stop_distance
        position_size_usd = position_size_btc * current_price
        
        # Aplikuj mnożnik kary
        position_size_usd *= (1 / self.penalty_multiplier)
        
        # Ogranicz do maksymalnego rozmiaru
        max_size = min(Config.MAX_POSITION_SIZE, Config.TRADE_AMOUNT_USDT)
        return min(position_size_usd, max_size)
    
    def calculate_stop_loss(self, entry_price: float, side: str, 
                           spread: float, atr: float) -> float:
        """Calculate stop loss based on spread and ATR."""
        # Stop loss = maksimum z (2× spread, 1× ATR)
        spread_based_stop = spread * Config.SPREAD_MULTIPLIER
        atr_based_stop = atr
        
        stop_distance = max(spread_based_stop, atr_based_stop)
        
        if side == 'long':
            return entry_price * (1 - stop_distance)
        else:  # short
            return entry_price * (1 + stop_distance)
    
    def record_trade(self, trade: Dict):
        """Record trade and apply penalties if necessary."""
        self.trade_history.append(trade)
        
        if trade.get('action') == 'close' and 'pnl' in trade:
            # Oblicz procentową stratę/zysk
            pnl_percent = trade['pnl'] / trade['size'] if trade['size'] > 0 else 0
            
            # Sprawdź progi kar
            if pnl_percent <= -Config.BIG_LOSS_THRESHOLD:
                # Duża strata - wyklucz strategię
                self._apply_strategy_exclusion(trade.get('reason', ''))
                self.last_big_loss_time = datetime.now()
            elif pnl_percent <= -Config.SMALL_LOSS_THRESHOLD:
                # Mała strata - zastosuj karę
                self._apply_penalty()
    
    def _apply_penalty(self):
        """Apply penalty multiplier for small losses."""
        self.penalty_multiplier = Config.PENALTY_MULTIPLIER
        print(f"Penalty applied: position size reduced by {self.penalty_multiplier}x")
    
    def _apply_strategy_exclusion(self, strategy: str):
        """Exclude strategy after big loss."""
        exclusion_end = datetime.now() + timedelta(seconds=Config.EXCLUSION_PERIOD)
        self.excluded_strategies[strategy] = exclusion_end
        print(f"Strategy '{strategy}' excluded until {exclusion_end}")
    
    def is_strategy_allowed(self, strategy: str) -> bool:
        """Check if strategy is currently allowed."""
        if strategy in self.excluded_strategies:
            if datetime.now() < self.excluded_strategies[strategy]:
                return False
            else:
                # Exclusion period ended
                del self.excluded_strategies[strategy]
        return True
    
    def reset_penalties(self):
        """Reset penalties after successful trades."""
        # Sprawdź ostatnie 3 transakcje
        recent_trades = self.trade_history[-3:]
        closed_trades = [t for t in recent_trades if t.get('action') == 'close']
        
        if len(closed_trades) >= 3:
            # Jeśli wszystkie są zyskowne, zresetuj kary
            if all(t.get('pnl', 0) > 0 for t in closed_trades):
                self.penalty_multiplier = 1.0
                print("Penalties reset after 3 profitable trades")
    
    def check_daily_loss_limit(self, daily_pnl: float) -> bool:
        """Check if daily loss limit is exceeded."""
        return daily_pnl > -Config.MAX_DAILY_LOSS
    
    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics."""
        return {
            'penalty_multiplier': self.penalty_multiplier,
            'excluded_strategies': list(self.excluded_strategies.keys()),
            'last_big_loss': self.last_big_loss_time.isoformat() if self.last_big_loss_time else None,
            'total_trades': len(self.trade_history)
        }