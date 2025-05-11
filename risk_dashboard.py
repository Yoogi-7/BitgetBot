# risk_dashboard.py
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import seaborn as sns
from datetime import datetime
import os
from typing import Dict, List


class RiskDashboard:
    """Real-time risk management dashboard."""
    
    def __init__(self, csv_file: str = 'trading_history.csv'):
        self.csv_file = csv_file
        self.fig, self.axes = plt.subplots(3, 2, figsize=(15, 12))
        self.fig.suptitle('Risk Management Dashboard', fontsize=16)
        
        # Set dark theme
        plt.style.use('dark_background')
        sns.set_palette("husl")
    
    def update_plots(self, frame):
        """Update all dashboard plots."""
        try:
            if not os.path.exists(self.csv_file):
                self._show_waiting_message()
                return
            
            # Load data
            df = pd.read_csv(self.csv_file)
            if df.empty:
                self._show_waiting_message()
                return
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Clear axes
            for ax in self.axes.flat:
                ax.clear()
            
            # Update plots
            self._plot_pnl_with_drawdown(df)
            self._plot_risk_metrics(df)
            self._plot_leverage_usage(df)
            self._plot_win_rate_by_strategy(df)
            self._plot_position_sizes(df)
            self._plot_risk_alerts(df)
            
            plt.tight_layout()
            
        except Exception as e:
            print(f"Error updating dashboard: {e}")
    
    def _plot_pnl_with_drawdown(self, df: pd.DataFrame):
        """Plot PnL with drawdown visualization."""
        ax = self.axes[0, 0]
        closed_trades = df[df['action'] == 'close'].copy()
        
        if not closed_trades.empty:
            closed_trades['cumulative_pnl'] = closed_trades['pnl'].cumsum()
            
            # Plot cumulative PnL
            ax.plot(closed_trades['timestamp'], closed_trades['cumulative_pnl'], 
                   color='cyan', linewidth=2, label='Cumulative PnL')
            
            # Calculate and plot drawdown
            peak = closed_trades['cumulative_pnl'].cummax()
            drawdown = closed_trades['cumulative_pnl'] - peak
            
            ax.fill_between(closed_trades['timestamp'], drawdown, 0, 
                           color='red', alpha=0.3, label='Drawdown')
            
            # Show current stats
            current_pnl = closed_trades['cumulative_pnl'].iloc[-1]
            max_dd = drawdown.min()
            
            ax.text(0.02, 0.98, f'PnL: ${current_pnl:.2f}\nMax DD: ${max_dd:.2f}', 
                   transform=ax.transAxes, va='top',
                   bbox=dict(boxstyle='round', facecolor='gray', alpha=0.8))
            
            ax.legend()
        
        ax.set_title('Cumulative PnL & Drawdown')
        ax.grid(True, alpha=0.3)
    
    def _plot_risk_metrics(self, df: pd.DataFrame):
        """Plot key risk metrics."""
        ax = self.axes[0, 1]
        closed_trades = df[df['action'] == 'close'].copy()
        
        if not closed_trades.empty:
            # Calculate daily PnL
            daily_pnl = closed_trades.set_index('timestamp')['pnl'].resample('D').sum()
            
            # Plot daily PnL bars
            colors = ['green' if x > 0 else 'red' for x in daily_pnl.values]
            ax.bar(daily_pnl.index, daily_pnl.values, color=colors, alpha=0.7)
            
            # Add max daily loss line
            max_daily_loss = -100  # Based on Config.MAX_DAILY_LOSS
            ax.axhline(y=max_daily_loss, color='red', linestyle='--', 
                      label=f'Max Daily Loss (${max_daily_loss})')
            
            # Risk metrics text
            win_rate = (closed_trades['pnl'] > 0).mean() * 100
            profit_factor = (closed_trades[closed_trades['pnl'] > 0]['pnl'].sum() / 
                           abs(closed_trades[closed_trades['pnl'] < 0]['pnl'].sum())
                           if not closed_trades[closed_trades['pnl'] < 0].empty else 0)
            
            metrics_text = f'Win Rate: {win_rate:.1f}%\nProfit Factor: {profit_factor:.2f}'
            ax.text(0.02, 0.02, metrics_text, transform=ax.transAxes,
                   bbox=dict(boxstyle='round', facecolor='gray', alpha=0.8))
            
            ax.legend()
        
        ax.set_title('Daily Risk Metrics')
        ax.grid(True, alpha=0.3)
    
    def _plot_leverage_usage(self, df: pd.DataFrame):
        """Plot leverage usage over time."""
        ax = self.axes[1, 0]
        
        if 'leverage' in df.columns:
            trades_with_leverage = df[df['leverage'].notna()].copy()
            
            if not trades_with_leverage.empty:
                # Plot leverage over time
                ax.scatter(trades_with_leverage['timestamp'], 
                          trades_with_leverage['leverage'],
                          c=trades_with_leverage['leverage'], 
                          cmap='RdYlGn_r', s=100, alpha=0.7)
                
                # Add moving average
                if len(trades_with_leverage) > 5:
                    ma_leverage = trades_with_leverage.set_index('timestamp')['leverage'].rolling('1D').mean()
                    ax.plot(ma_leverage.index, ma_leverage.values, 
                           color='yellow', linewidth=2, label='MA Leverage')
                
                # Add max leverage line
                ax.axhline(y=30, color='orange', linestyle='--', label='High Leverage Warning')
                ax.axhline(y=50, color='red', linestyle='--', label='Max Leverage')
                
                ax.legend()
                
                # Current average leverage
                avg_leverage = trades_with_leverage['leverage'].mean()
                ax.text(0.02, 0.98, f'Avg Leverage: {avg_leverage:.1f}x', 
                       transform=ax.transAxes, va='top',
                       bbox=dict(boxstyle='round', facecolor='gray', alpha=0.8))
        
        ax.set_title('Leverage Usage')
        ax.set_ylabel('Leverage')
        ax.grid(True, alpha=0.3)
    
    def _plot_win_rate_by_strategy(self, df: pd.DataFrame):
        """Plot win rate by trading strategy."""
        ax = self.axes[1, 1]
        closed_trades = df[df['action'] == 'close'].copy()
        
        if not closed_trades.empty and 'reason' in closed_trades.columns:
            # Extract strategy from reason
            closed_trades['strategy'] = closed_trades['reason'].str.extract(r'([A-Za-z]+)')
            
            # Calculate win rate by strategy
            strategy_stats = closed_trades.groupby('strategy').agg({
                'pnl': ['count', lambda x: (x > 0).mean() * 100, 'sum']
            }).round(1)
            
            if not strategy_stats.empty:
                strategies = strategy_stats.index
                win_rates = strategy_stats[('pnl', '<lambda>')]
                trade_counts = strategy_stats[('pnl', 'count')]
                
                # Create bar plot
                bars = ax.bar(strategies, win_rates, color='skyblue', alpha=0.7)
                
                # Add trade count on top of bars
                for bar, count in zip(bars, trade_counts):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(count)} trades',
                           ha='center', va='bottom')
                
                ax.axhline(y=50, color='white', linestyle='--', alpha=0.5)
                ax.set_ylabel('Win Rate %')
                ax.set_ylim(0, 100)
        
        ax.set_title('Win Rate by Strategy')
        ax.grid(True, alpha=0.3)
    
    def _plot_position_sizes(self, df: pd.DataFrame):
        """Plot position sizes and risk per trade."""
        ax = self.axes[2, 0]
        open_trades = df[df['action'] == 'open'].copy()
        
        if not open_trades.empty and 'size' in open_trades.columns:
            # Plot position sizes over time
            ax.plot(open_trades['timestamp'], open_trades['size'], 
                   marker='o', linestyle='-', color='cyan', alpha=0.7)
            
            # Add risk per trade line (assuming 1% risk)
            if 'balance_after' in open_trades.columns:
                risk_limit = open_trades['balance_after'] * 0.01
                ax.plot(open_trades['timestamp'], risk_limit, 
                       color='red', linestyle='--', label='1% Risk Limit')
            
            # Highlight high-risk trades
            high_risk = open_trades['size'] > open_trades['size'].mean() * 1.5
            if high_risk.any():
                ax.scatter(open_trades.loc[high_risk, 'timestamp'], 
                          open_trades.loc[high_risk, 'size'],
                          color='red', s=100, label='High Risk Trades')
            
            ax.legend()
        
        ax.set_title('Position Sizing & Risk')
        ax.set_ylabel('Position Size (USD)')
        ax.grid(True, alpha=0.3)
    
    def _plot_risk_alerts(self, df: pd.DataFrame):
        """Display current risk alerts and warnings."""
        ax = self.axes[2, 1]
        ax.axis('off')
        
        # Create risk alert panel
        alerts = self._generate_risk_alerts(df)
        
        # Background
        ax.add_patch(plt.Rectangle((0.05, 0.05), 0.9, 0.9, 
                                 facecolor='#1a1a1a', 
                                 edgecolor='red' if alerts['high_risk'] else 'green', 
                                 linewidth=3))
        
        # Display alerts
        alert_text = "RISK ALERTS\n\n"
        for alert, status in alerts.items():
            if alert != 'high_risk':
                icon = "🚨" if status['triggered'] else "✅"
                alert_text += f"{icon} {status['message']}\n"
        
        ax.text(0.5, 0.5, alert_text, 
               transform=ax.transAxes,
               ha='center', va='center',
               fontsize=12, 
               color='white',
               family='monospace')
        
        ax.set_title('Risk Alert Panel')
    
    def _generate_risk_alerts(self, df: pd.DataFrame) -> Dict:
        """Generate current risk alerts based on data."""
        alerts = {
            'daily_loss': {'triggered': False, 'message': 'Daily Loss: OK'},
            'consecutive_losses': {'triggered': False, 'message': 'Consecutive Losses: 0'},
            'leverage': {'triggered': False, 'message': 'Leverage: Normal'},
            'position_concentration': {'triggered': False, 'message': 'Position Concentration: OK'},
            'high_risk': False
        }
        
        closed_trades = df[df['action'] == 'close'].copy()
        
        if not closed_trades.empty:
            # Check daily loss
            today_pnl = closed_trades[closed_trades['timestamp'].dt.date == pd.Timestamp.now().date()]['pnl'].sum()
            if today_pnl < -50:  # Example threshold
                alerts['daily_loss']['triggered'] = True
                alerts['daily_loss']['message'] = f'Daily Loss: ${today_pnl:.2f} ⚠️'
            else:
                alerts['daily_loss']['message'] = f'Daily Loss: ${today_pnl:.2f}'
            
            # Check consecutive losses
            last_5_trades = closed_trades.tail(5)
            consecutive_losses = 0
            for _, trade in last_5_trades.iterrows():
                if trade['pnl'] < 0:
                    consecutive_losses += 1
                else:
                    consecutive_losses = 0
            
            if consecutive_losses >= 2:
                alerts['consecutive_losses']['triggered'] = True
                alerts['consecutive_losses']['message'] = f'Consecutive Losses: {consecutive_losses} ⚠️'
            else:
                alerts['consecutive_losses']['message'] = f'Consecutive Losses: {consecutive_losses}'
            
            # Check leverage
            if 'leverage' in df.columns:
                recent_leverage = df['leverage'].tail(5).mean()
                if recent_leverage > 30:
                    alerts['leverage']['triggered'] = True
                    alerts['leverage']['message'] = f'Leverage: {recent_leverage:.1f}x ⚠️'
                else:
                    alerts['leverage']['message'] = f'Leverage: {recent_leverage:.1f}x'
        
        # Overall high risk assessment
        alerts['high_risk'] = sum(alert['triggered'] for alert in alerts.values() if isinstance(alert, dict)) >= 2
        
        return alerts
    
    def _show_waiting_message(self):
        """Show waiting message when no data available."""
        for ax in self.axes.flat:
            ax.clear()
            ax.text(0.5, 0.5, 'Waiting for trading data...', 
                   transform=ax.transAxes, ha='center', va='center', 
                   fontsize=14, color='yellow')
            ax.axis('off')
    
    def start(self, interval: int = 5000):
        """Start the dashboard with auto-refresh."""
        print("Starting Risk Management Dashboard...")
        print("Press Ctrl+C to stop")
        
        # Animation
        ani = FuncAnimation(self.fig, self.update_plots, 
                          interval=interval, 
                          cache_frame_data=False)
        
        plt.show()


if __name__ == "__main__":
    dashboard = RiskDashboard()
    dashboard.start()