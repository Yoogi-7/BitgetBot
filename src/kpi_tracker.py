# src/kpi_tracker.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging


class KPITracker:
    """Track Key Performance Indicators and implement signal flow."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.kpi_history = []
        self.signal_flow_log = []
        
        # KPI Thresholds
        self.MAX_DAILY_DRAWDOWN = 0.02  # 2% dziennie
        self.TARGET_HOLD_TIME = (2, 5)  # 2-5 minut
        self.MIN_RISK_REWARD = 1.2  # Minimum 1:2
        
        # Signal flow parameters
        self.RSI_THRESHOLD = 25
        self.ORDER_BOOK_IMBALANCE_THRESHOLD = 0.65
        self.STOP_LOSS_PERCENT = 0.3
        self.TAKE_PROFIT_RANGE = (0.5, 0.8)  # 0.5-0.8% zysku
        self.TIME_BASED_EXIT = 300  # 5 minut
    
    def process_signal_flow(self, market_data: Dict, indicators: Dict) -> Dict:
        """Process signal flow according to example workflow."""
        signal_result = {
            'action': None,
            'side': None,
            'confidence': 0,
            'stop_loss': None,
            'take_profit': None,
            'exit_time': None,
            'flow_log': []
        }
        
        try:
            # 1. Wejście: 1-minutowa świeża świeca BTC/USDT + order book L2
            current_price = market_data.get('ticker', {}).get('last', 0)
            order_book = market_data.get('order_book', {})
            
            signal_result['flow_log'].append(f"Received data - Price: {current_price}")
            
            # 2. Przetwarzanie: Model sprawdza RSI(5), VWAP i imbalance
            rsi_5 = indicators.get('rsi_5', 50)
            vwap = indicators.get('vwap', current_price)
            
            # Calculate order book imbalance
            imbalance = self._calculate_order_book_imbalance(order_book)
            
            signal_result['flow_log'].append(
                f"Indicators - RSI(5): {rsi_5:.1f}, VWAP: {vwap:.2f}, Imbalance: {imbalance:.2f}"
            )
            
            # Check buy signal conditions
            if rsi_5 < self.RSI_THRESHOLD and imbalance > self.ORDER_BOOK_IMBALANCE_THRESHOLD:
                signal_result['action'] = 'OPEN'
                signal_result['side'] = 'long'
                signal_result['confidence'] = 0.8
                
                # 3. Ryzyko: Stop-loss ustawiony na 0.3% poniżej ceny wejścia
                signal_result['stop_loss'] = current_price * (1 - self.STOP_LOSS_PERCENT / 100)
                
                # 4. Wyjście: Take-profit na 0.5-0.8% zysku lub po 5 minutach
                take_profit_pct = np.random.uniform(*self.TAKE_PROFIT_RANGE)  # Random within range
                signal_result['take_profit'] = current_price * (1 + take_profit_pct / 100)
                signal_result['exit_time'] = datetime.now() + timedelta(seconds=self.TIME_BASED_EXIT)
                
                signal_result['flow_log'].append(
                    f"BUY Signal - Stop Loss: {signal_result['stop_loss']:.2f}, "
                    f"Take Profit: {signal_result['take_profit']:.2f}"
                )
            else:
                signal_result['flow_log'].append(
                    f"No signal - Conditions not met (RSI<{self.RSI_THRESHOLD} and Imbalance>{self.ORDER_BOOK_IMBALANCE_THRESHOLD})"
                )
            
            # Log the signal flow
            self._log_signal_flow(signal_result)
            
        except Exception as e:
            self.logger.error(f"Error in signal flow processing: {e}")
            signal_result['flow_log'].append(f"Error: {str(e)}")
        
        return signal_result
    
    def _calculate_order_book_imbalance(self, order_book: Dict) -> float:
        """Calculate order book imbalance."""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return 0.5  # Neutral
            
            # Calculate bid volume for top levels
            bid_volume = sum(float(size) for _, size in bids[:5])
            
            # Calculate ask volume for top levels
            ask_volume = sum(float(size) for _, size in asks[:5])
            
            total_volume = bid_volume + ask_volume
            
            if total_volume > 0:
                # Imbalance: proportion of bid volume
                return bid_volume / total_volume
            
            return 0.5  # Neutral
            
        except Exception as e:
            self.logger.error(f"Error calculating order book imbalance: {e}")
            return 0.5
    
    def track_trade_kpi(self, trade: Dict):
        """Track KPIs for a completed trade."""
        try:
            # Calculate trade metrics
            hold_time = (trade['exit_time'] - trade['entry_time']).total_seconds() / 60
            risk_reward = abs(trade['pnl']) / trade.get('risk_amount', 1) if trade['pnl'] > 0 else 0
            
            kpi_data = {
                'timestamp': datetime.now(),
                'hold_time_minutes': hold_time,
                'risk_reward_ratio': risk_reward,
                'pnl': trade['pnl'],
                'pnl_percent': trade['pnl_percent'],
                'achieved_target_hold_time': self.TARGET_HOLD_TIME[0] <= hold_time <= self.TARGET_HOLD_TIME[1],
                'achieved_risk_reward': risk_reward >= self.MIN_RISK_REWARD
            }
            
            self.kpi_history.append(kpi_data)
            
            # Check KPI compliance
            self._check_kpi_compliance(kpi_data)
            
        except Exception as e:
            self.logger.error(f"Error tracking trade KPI: {e}")
    
    def check_daily_drawdown(self, current_balance: float, starting_balance: float) -> bool:
        """Check if daily drawdown limit is exceeded."""
        drawdown = (starting_balance - current_balance) / starting_balance
        
        if drawdown >= self.MAX_DAILY_DRAWDOWN:
            self.logger.warning(f"Daily drawdown limit reached: {drawdown*100:.1f}%")
            return False
        
        return True
    
    def get_kpi_summary(self) -> Dict:
        """Get summary of KPI metrics."""
        if not self.kpi_history:
            return {
                'total_trades': 0,
                'avg_hold_time': 0,
                'avg_risk_reward': 0,
                'kpi_compliance_rate': 0
            }
        
        df = pd.DataFrame(self.kpi_history)
        
        summary = {
            'total_trades': len(df),
            'avg_hold_time': df['hold_time_minutes'].mean(),
            'avg_risk_reward': df['risk_reward_ratio'].mean(),
            'target_hold_time_rate': df['achieved_target_hold_time'].mean() * 100,
            'target_risk_reward_rate': df['achieved_risk_reward'].mean() * 100,
            'max_drawdown_day': df.groupby(df['timestamp'].dt.date)['pnl_percent'].sum().min()
        }
        
        # Overall KPI compliance
        summary['kpi_compliance_rate'] = (
            summary['target_hold_time_rate'] * 0.3 +
            summary['target_risk_reward_rate'] * 0.4 +
            (100 if summary['max_drawdown_day'] > -2 else 0) * 0.3
        )
        
        return summary
    
    def _check_kpi_compliance(self, kpi_data: Dict):
        """Check if trade meets KPI requirements."""
        warnings = []
        
        if not kpi_data['achieved_target_hold_time']:
            warnings.append(f"Hold time {kpi_data['hold_time_minutes']:.1f}min outside target {self.TARGET_HOLD_TIME}")
        
        if not kpi_data['achieved_risk_reward']:
            warnings.append(f"Risk/Reward {kpi_data['risk_reward_ratio']:.2f} below target {self.MIN_RISK_REWARD}")
        
        if warnings:
            for warning in warnings:
                self.logger.warning(f"KPI Warning: {warning}")
    
    def _log_signal_flow(self, signal_result: Dict):
        """Log signal flow for analysis."""
        log_entry = {
            'timestamp': datetime.now(),
            'action': signal_result['action'],
            'side': signal_result.get('side'),
            'confidence': signal_result.get('confidence', 0),
            'flow_steps': signal_result['flow_log']
        }
        
        self.signal_flow_log.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.signal_flow_log) > 1000:
            self.signal_flow_log = self.signal_flow_log[-1000:]
    
    def export_kpi_report(self, filename: str = None):
        """Export KPI report to file."""
        if not filename:
            filename = f"kpi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'summary': self.get_kpi_summary(),
            'kpi_history': self.kpi_history[-100:],  # Last 100 trades
            'signal_flow_examples': self.signal_flow_log[-10:],  # Last 10 signal flows
            'generated_at': datetime.now().isoformat()
        }
        
        pd.DataFrame([report]).to_json(filename, orient='records', indent=2)
        self.logger.info(f"KPI report exported to {filename}")
        
        return filename