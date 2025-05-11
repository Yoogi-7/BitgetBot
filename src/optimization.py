# src/optimization.py
import schedule
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from src.ml_models import MLPredictor
from config.settings import Config


class ContinuousOptimizer:
    """Continuous optimization and monitoring system."""
    
    def __init__(self, bot=None):
        self.logger = logging.getLogger(__name__)
        self.bot = bot
        self.ml_predictor = MLPredictor(use_ml=Config.USE_ML_MODELS)
        
        # Monitoring state
        self.correlation_matrix = {}
        self.false_signal_log = []
        self.last_retrain_time = datetime.now()
        
        # Schedule tasks
        self._schedule_tasks()
    
    def _schedule_tasks(self):
        """Schedule optimization tasks."""
        # Retrain model every 24 hours
        schedule.every(24).hours.do(self.retrain_models)
        
        # Monitor correlations every hour
        schedule.every(1).hour.do(self.monitor_correlations)
        
        # Analyze false signals every 6 hours
        schedule.every(6).hours.do(self.analyze_false_signals)
        
        # Daily performance report
        schedule.every().day.at("00:00").do(self.generate_daily_report)
        
        self.logger.info("Optimization tasks scheduled")
    
    def start(self):
        """Start optimization scheduler."""
        self.logger.info("Starting continuous optimization")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
    
    def retrain_models(self):
        """Retrain ML models with latest data."""
        try:
            self.logger.info("Starting model retraining...")
            
            # Get recent data
            if self.bot and self.bot.exchange:
                df = self.bot.exchange.get_ohlcv(limit=1000)
                
                if df is not None and not df.empty:
                    # Prepare training data
                    X, y = self._prepare_training_data(df)
                    
                    # Retrain model
                    if self.ml_predictor:
                        self.ml_predictor.train(X, y)
                        self.last_retrain_time = datetime.now()
                        self.logger.info("Model retraining completed")
                    
            else:
                self.logger.warning("No bot instance available for retraining")
                
        except Exception as e:
            self.logger.error(f"Error during model retraining: {e}")
    
    def monitor_correlations(self):
        """Monitor correlation changes between trading pairs."""
        try:
            pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']  # Example pairs
            correlations = {}
            
            for pair in pairs:
                if self.bot and self.bot.exchange:
                    # Get data for each pair
                    df = self.bot.exchange.get_ohlcv(symbol=pair, limit=100)
                    if df is not None:
                        correlations[pair] = df['close'].pct_change()
            
            # Calculate correlation matrix
            if correlations:
                corr_df = pd.DataFrame(correlations)
                new_corr_matrix = corr_df.corr()
                
                # Check for significant changes
                if self.correlation_matrix:
                    changes = new_corr_matrix - self.correlation_matrix
                    significant_changes = changes[abs(changes) > 0.2]
                    
                    if not significant_changes.empty:
                        self.logger.warning(f"Significant correlation changes detected: {significant_changes}")
                        
                        # Notify about changes
                        if self.bot and self.bot.notifier:
                            message = "⚠️ Correlation Alert\nSignificant changes in pair correlations detected"
                            self.bot.notifier.send_message(message)
                
                self.correlation_matrix = new_corr_matrix
                
        except Exception as e:
            self.logger.error(f"Error monitoring correlations: {e}")
    
    def analyze_false_signals(self):
        """Analyze false signals during low liquidity periods."""
        try:
            if not self.bot or not self.bot.trade_logger:
                return
            
            # Read trading history
            df = pd.read_csv('trading_history.csv')
            if df.empty:
                return
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            
            # Identify losing trades
            losing_trades = df[(df['action'] == 'close') & (df['pnl'] < 0)]
            
            # Analyze by hour (liquidity proxy)
            hourly_stats = losing_trades.groupby('hour').agg({
                'pnl': ['count', 'sum', 'mean']
            })
            
            # Identify problematic hours (low liquidity)
            low_liquidity_hours = []
            for hour in range(24):
                if hour not in range(*Config.HIGH_LIQUIDITY_HOURS):
                    if hour in hourly_stats.index:
                        loss_count = hourly_stats.loc[hour, ('pnl', 'count')]
                        avg_loss = hourly_stats.loc[hour, ('pnl', 'mean')]
                        
                        if loss_count > 3 and avg_loss < -10:  # Threshold
                            low_liquidity_hours.append(hour)
                            self.false_signal_log.append({
                                'hour': hour,
                                'loss_count': loss_count,
                                'avg_loss': avg_loss,
                                'timestamp': datetime.now()
                            })
            
            if low_liquidity_hours:
                self.logger.warning(f"High false signal rate during hours: {low_liquidity_hours}")
                
                # Adjust strategy for these hours
                if self.bot and hasattr(self.bot, 'strategy'):
                    self.bot.strategy.low_liquidity_hours = low_liquidity_hours
            
        except Exception as e:
            self.logger.error(f"Error analyzing false signals: {e}")
    
    def _prepare_training_data(self, df: pd.DataFrame) -> tuple:
        """Prepare data for model training."""
        # Calculate features
        features = []
        labels = []
        
        # Add technical indicators
        df['rsi'] = self._calculate_rsi(df['close'])
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['price_change'] = df['close'].pct_change()
        
        # Create labels (future price direction)
        df['future_return'] = df['close'].shift(-5) / df['close'] - 1
        df['label'] = np.where(df['future_return'] > 0.001, 1, 
                              np.where(df['future_return'] < -0.001, -1, 0))
        
        # Prepare feature matrix
        feature_cols = ['rsi', 'volume_ratio', 'price_change']
        df = df.dropna()
        
        X = df[feature_cols].values
        y = df['label'].values
        
        return X, y
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_daily_report(self):
        """Generate comprehensive daily performance report."""
        try:
            if not self.bot:
                return
            
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'model_performance': self._analyze_model_performance(),
                'risk_metrics': self._calculate_risk_metrics(),
                'optimization_status': {
                    'last_retrain': self.last_retrain_time.isoformat(),
                    'correlation_changes': len(self.correlation_matrix) > 0,
                    'false_signals_detected': len(self.false_signal_log)
                }
            }
            
            # Save report
            report_file = f"optimization_report_{report['date']}.json"
            pd.DataFrame([report]).to_json(report_file, orient='records', indent=2)
            
            # Send summary via Telegram
            if self.bot.notifier:
                summary = f"""
📊 Daily Optimization Report - {report['date']}
Model Accuracy: {report['model_performance'].get('accuracy', 0):.1f}%
Win Rate: {report['risk_metrics'].get('win_rate', 0):.1f}%
Profit Factor: {report['risk_metrics'].get('profit_factor', 0):.2f}
Last Retrain: {self.last_retrain_time.strftime('%H:%M')}
False Signals: {len(self.false_signal_log)}
                """
                self.bot.notifier.send_message(summary)
            
            self.logger.info(f"Daily report generated: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")
    
    def _analyze_model_performance(self) -> Dict:
        """Analyze ML model performance metrics."""
        performance = {
            'accuracy': 0,
            'precision': 0,
            'recall': 0,
            'signals_generated': 0
        }
        
        try:
            # This would integrate with actual ML model metrics
            if self.ml_predictor and hasattr(self.ml_predictor, 'performance_metrics'):
                performance.update(self.ml_predictor.performance_metrics)
        except Exception as e:
            self.logger.error(f"Error analyzing model performance: {e}")
        
        return performance
    
    def _calculate_risk_metrics(self) -> Dict:
        """Calculate risk management metrics."""
        metrics = {
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0
        }
        
        try:
            if self.bot and self.bot.risk_manager:
                risk_metrics = self.bot.risk_manager.get_risk_metrics()
                
                # Read trading history for additional metrics
                df = pd.read_csv('trading_history.csv')
                if not df.empty:
                    closed_trades = df[df['action'] == 'close']
                    
                    if not closed_trades.empty:
                        winning_trades = closed_trades[closed_trades['pnl'] > 0]
                        metrics['win_rate'] = len(winning_trades) / len(closed_trades) * 100
                        
                        total_profit = closed_trades[closed_trades['pnl'] > 0]['pnl'].sum()
                        total_loss = abs(closed_trades[closed_trades['pnl'] < 0]['pnl'].sum())
                        
                        if total_loss > 0:
                            metrics['profit_factor'] = total_profit / total_loss
                        
                        # Sharpe ratio (simplified)
                        returns = closed_trades['pnl'].pct_change().dropna()
                        if len(returns) > 0 and returns.std() != 0:
                            metrics['sharpe_ratio'] = np.sqrt(252) * (returns.mean() / returns.std())
                        
                        metrics.update(risk_metrics)
                        
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
        
        return metrics


# Alert system integration
class AlertSystem:
    """Trading alert system with sound and visual notifications."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.alerts_enabled = True
        
    def send_alert(self, signal_type: str, message: str, priority: str = 'medium'):
        """Send trading alert with appropriate notification method."""
        if not self.alerts_enabled:
            return
        
        try:
            # Console notification
            self.logger.info(f"ALERT [{priority.upper()}]: {message}")
            
            # Sound notification (platform-dependent)
            if priority == 'high':
                self._play_sound('alert_high.wav')
            elif priority == 'medium':
                self._play_sound('alert_medium.wav')
            
            # Visual notification (would integrate with TradingView or similar)
            self._send_visual_alert(signal_type, message, priority)
            
        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
    
    def _play_sound(self, sound_file: str):
        """Play alert sound (platform-dependent implementation)."""
        try:
            # This would use platform-specific sound libraries
            # For example: winsound on Windows, ossaudiodev on Linux
            pass
        except Exception as e:
            self.logger.error(f"Error playing sound: {e}")
    
    def _send_visual_alert(self, signal_type: str, message: str, priority: str):
        """Send visual alert (e.g., to TradingView)."""
        try:
            # This would integrate with TradingView webhook or similar
            webhook_data = {
                'signal_type': signal_type,
                'message': message,
                'priority': priority,
                'timestamp': datetime.now().isoformat()
            }
            
            # Example: Send to TradingView webhook
            # requests.post(TRADINGVIEW_WEBHOOK_URL, json=webhook_data)
            
        except Exception as e:
            self.logger.error(f"Error sending visual alert: {e}")


# Enhanced bot with real-time integration
class EnhancedTradingBot:
    """Enhanced trading bot with WebSocket and optimization integration."""
    
    def __init__(self):
        # Existing bot components
        super().__init__()
        
        # Add new components
        self.websocket_client = None
        self.optimizer = ContinuousOptimizer(self)
        self.alert_system = AlertSystem()
        
    async def start_realtime(self):
        """Start bot with real-time WebSocket integration."""
        # Initialize WebSocket client
        self.websocket_client = WebSocketClient(
            on_data_callback=self._on_market_data,
            on_signal_callback=self._on_trading_signal
        )
        
        await self.websocket_client.initialize()
        
        # Start optimization scheduler in background
        import threading
        optimizer_thread = threading.Thread(target=self.optimizer.start)
        optimizer_thread.daemon = True
        optimizer_thread.start()
        
        # Connect to WebSocket and start trading
        await self.websocket_client.connect()
    
    async def _on_market_data(self, data: Dict):
        """Process real-time market data."""
        # Update internal state with real-time data
        pass
    
    async def _on_trading_signal(self, priority: int, signal_data: Dict):
        """Process trading signals with priority system."""
        if priority == 1:  # Strong signal - auto-execute
            self.alert_system.send_alert(
                'trade',
                f"Strong signal detected: {signal_data['reason']}",
                'high'
            )
            # Execute trade automatically
            # self.execute_trade(signal_data)
            
        elif priority == 3:  # Weak signal - require confirmation
            self.alert_system.send_alert(
                'confirm',
                f"Weak signal needs confirmation: {signal_data['reason']}",
                'low'
            )
            # Wait for second model confirmation
            # self.request_confirmation(signal_data)


if __name__ == "__main__":
    # Example usage
    optimizer = ContinuousOptimizer()
    optimizer.start()