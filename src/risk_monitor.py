# src/risk_monitor.py
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List
from config.settings import Config
from src.notifier import TelegramNotifier


class RiskMonitor:
    """Real-time risk monitoring and alerting system."""
    
    def __init__(self, risk_manager, positions_tracker):
        self.logger = logging.getLogger(__name__)
        self.risk_manager = risk_manager
        self.positions_tracker = positions_tracker
        self.notifier = TelegramNotifier()
        
        # Alert thresholds
        self.alerts = {
            'daily_loss_warning': {'threshold': 0.5, 'sent': False},  # 50% of max daily loss
            'daily_loss_critical': {'threshold': 0.8, 'sent': False}, # 80% of max daily loss
            'leverage_high': {'threshold': 30, 'sent': False},       # High leverage warning
            'consecutive_losses': {'threshold': 2, 'sent': False}     # Near max consecutive losses
        }
        
        # Monitoring thread
        self.monitoring = True
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start the monitoring thread."""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        self.logger.info("Risk monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        self.logger.info("Risk monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                self._check_risk_metrics()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in risk monitoring: {e}")
    
    def _check_risk_metrics(self):
        """Check all risk metrics and send alerts if needed."""
        risk_report = self.risk_manager.get_risk_report()
        
        # Check daily loss
        daily_loss_percent = abs(risk_report['daily_pnl_percent'])
        max_loss = Config.MAX_DAILY_LOSS_PERCENT
        
        # Warning at 50% of max daily loss
        if daily_loss_percent >= max_loss * self.alerts['daily_loss_warning']['threshold']:
            if not self.alerts['daily_loss_warning']['sent']:
                self._send_alert(
                    "⚠️ Daily Loss Warning",
                    f"Daily loss reached {daily_loss_percent:.1f}% "
                    f"(warning at {max_loss * 0.5:.1f}%)"
                )
                self.alerts['daily_loss_warning']['sent'] = True
        
        # Critical at 80% of max daily loss
        if daily_loss_percent >= max_loss * self.alerts['daily_loss_critical']['threshold']:
            if not self.alerts['daily_loss_critical']['sent']:
                self._send_alert(
                    "🚨 Daily Loss Critical",
                    f"Daily loss reached {daily_loss_percent:.1f}% "
                    f"(limit at {max_loss:.1f}%)",
                    priority='high'
                )
                self.alerts['daily_loss_critical']['sent'] = True
        
        # Check consecutive losses
        consecutive_losses = risk_report['consecutive_losses']
        if consecutive_losses >= self.alerts['consecutive_losses']['threshold']:
            if not self.alerts['consecutive_losses']['sent']:
                self._send_alert(
                    "⚠️ Consecutive Losses Warning",
                    f"{consecutive_losses} consecutive losses "
                    f"(system pauses at {Config.MAX_CONSECUTIVE_LOSSES})"
                )
                self.alerts['consecutive_losses']['sent'] = True
        
        # Check high leverage usage
        self._check_leverage_usage()
        
        # Reset alerts at new day
        self._reset_daily_alerts()
    
    def _check_leverage_usage(self):
        """Check current leverage usage across positions."""
        high_leverage_positions = []
        
        for symbol, positions in self.positions_tracker.items():
            for position in positions:
                leverage = position.get('leverage', Config.BASE_LEVERAGE)
                if leverage >= self.alerts['leverage_high']['threshold']:
                    high_leverage_positions.append({
                        'symbol': symbol,
                        'leverage': leverage,
                        'size': position.get('size_usd', 0)
                    })
        
        if high_leverage_positions and not self.alerts['leverage_high']['sent']:
            message = "High leverage positions detected:\n"
            for pos in high_leverage_positions:
                message += f"• {pos['symbol']}: {pos['leverage']}x (${pos['size']:.2f})\n"
            
            self._send_alert("⚠️ High Leverage Warning", message)
            self.alerts['leverage_high']['sent'] = True
    
    def _send_alert(self, title: str, message: str, priority: str = 'normal'):
        """Send alert notification."""
        full_message = f"<b>{title}</b>\n\n{message}"
        
        if priority == 'high':
            # Add urgency indicators for high priority
            full_message = "🚨🚨🚨\n" + full_message + "\n🚨🚨🚨"
        
        self.notifier.send_message(full_message)
        self.logger.warning(f"{title}: {message}")
    
    def _reset_daily_alerts(self):
        """Reset daily alerts at the start of a new day."""
        current_hour = datetime.now().hour
        if current_hour == 0 and any(alert['sent'] for alert in self.alerts.values()):
            for alert in self.alerts.values():
                alert['sent'] = False
            self.logger.info("Daily alerts reset")
    
    def get_risk_summary(self) -> Dict:
        """Get current risk summary."""
        risk_report = self.risk_manager.get_risk_report()
        
        return {
            'daily_pnl': risk_report['daily_pnl'],
            'daily_pnl_percent': risk_report['daily_pnl_percent'],
            'consecutive_losses': risk_report['consecutive_losses'],
            'system_status': 'PAUSED' if risk_report['system_paused'] else 'ACTIVE',
            'leverage_multiplier': risk_report['leverage_multiplier'],
            'alerts_triggered': sum(1 for alert in self.alerts.values() if alert['sent'])
        }