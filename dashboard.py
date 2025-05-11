# dashboard.py
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime
import os
from typing import Optional


class TradingDashboard:
    """Simplified real-time trading dashboard."""
    
    def __init__(self, csv_file: str = 'trading_history.csv'):
        self.csv_file = csv_file
        self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 8))
        self.fig.suptitle('Trading Bot Dashboard', fontsize=16)
        
        # Dark theme
        plt.style.use('dark_background')
    
    def update_plots(self, frame):
        """Update dashboard plots."""
        try:
            # Check if data exists
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
            self._plot_pnl(df)
            self._plot_balance(df)
            self._plot_trade_distribution(df)
            self._plot_statistics(df)
            
            plt.tight_layout()
            
        except Exception as e:
            print(f"Error updating dashboard: {e}")
    
    def _show_waiting_message(self):
        """Show waiting message when no data."""
        for ax in self.axes.flat:
            ax.clear()
            ax.text(0.5, 0.5, 'Waiting for trading data...', 
                   transform=ax.transAxes, ha='center', va='center', 
                   fontsize=14, color='yellow')
            ax.axis('off')
    
    def _plot_pnl(self, df: pd.DataFrame):
        """Plot cumulative PnL."""
        ax = self.axes[0, 0]
        closed_trades = df[df['action'] == 'close'].copy()
        
        if not closed_trades.empty:
            closed_trades['cumulative_pnl'] = closed_trades['pnl'].cumsum()
            color = 'green' if closed_trades['cumulative_pnl'].iloc[-1] >= 0 else 'red'
            
            ax.plot(closed_trades['timestamp'], closed_trades['cumulative_pnl'], 
                   color=color, linewidth=2)
            ax.fill_between(closed_trades['timestamp'], 0, closed_trades['cumulative_pnl'], 
                           color=color, alpha=0.3)
            
            # Show final value
            last_pnl = closed_trades['cumulative_pnl'].iloc[-1]
            ax.text(0.98, 0.98, f'${last_pnl:.2f}', 
                   transform=ax.transAxes, ha='right', va='top', 
                   fontsize=14, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
        
        ax.set_title('Cumulative PnL', fontsize=14)
        ax.set_ylabel('PnL (USDT)')
        ax.grid(True, alpha=0.3)
    
    def _plot_balance(self, df: pd.DataFrame):
        """Plot account balance."""
        ax = self.axes[0, 1]
        
        if 'balance_after' in df.columns:
            balance_data = df[df['balance_after'] > 0].copy()
            
            if not balance_data.empty:
                ax.plot(balance_data['timestamp'], balance_data['balance_after'], 
                       color='cyan', linewidth=2)
                
                # Calculate change
                start_balance = balance_data['balance_after'].iloc[0]
                end_balance = balance_data['balance_after'].iloc[-1]
                pct_change = ((end_balance - start_balance) / start_balance) * 100
                color = 'green' if pct_change >= 0 else 'red'
                
                ax.text(0.98, 0.98, f'${end_balance:.2f}\n({pct_change:+.1f}%)', 
                       transform=ax.transAxes, ha='right', va='top', 
                       fontsize=14, fontweight='bold',
                       bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
        
        ax.set_title('Account Balance', fontsize=14)
        ax.set_ylabel('Balance (USDT)')
        ax.grid(True, alpha=0.3)
    
    def _plot_trade_distribution(self, df: pd.DataFrame):
        """Plot PnL distribution."""
        ax = self.axes[1, 0]
        closed_trades = df[df['action'] == 'close'].copy()
        
        if not closed_trades.empty:
            # Separate wins and losses
            profits = closed_trades[closed_trades['pnl'] > 0]['pnl']
            losses = closed_trades[closed_trades['pnl'] < 0]['pnl']
            
            # Plot histogram
            if not profits.empty:
                ax.hist(profits, bins=15, color='green', alpha=0.6, label='Profits')
            if not losses.empty:
                ax.hist(losses, bins=15, color='red', alpha=0.6, label='Losses')
            
            ax.axvline(x=0, color='white', linestyle='--', alpha=0.5)
            ax.legend()
            
            # Show average
            avg_pnl = closed_trades['pnl'].mean()
            ax.axvline(x=avg_pnl, color='yellow', linestyle='-', linewidth=2)
            ax.text(avg_pnl, ax.get_ylim()[1]*0.9, f'Avg: ${avg_pnl:.2f}', 
                   ha='center', color='yellow', fontweight='bold')
        
        ax.set_title('PnL Distribution', fontsize=14)
        ax.set_xlabel('PnL (USDT)')
        ax.set_ylabel('Frequency')
        ax.grid(True, alpha=0.3)
    
    def _plot_statistics(self, df: pd.DataFrame):
        """Plot trading statistics."""
        ax = self.axes[1, 1]
        ax.axis('off')
        
        stats_text = self._generate_stats_text(df)
        
        # Background box
        ax.add_patch(plt.Rectangle((0.05, 0.05), 0.9, 0.9, 
                                 facecolor='#1a1a1a', 
                                 edgecolor='cyan', 
                                 linewidth=2))
        
        ax.text(0.5, 0.5, stats_text, 
               transform=ax.transAxes,
               ha='center', va='center',
               fontsize=12, 
               color='white',
               family='monospace')
        
        ax.set_title('Trading Statistics', fontsize=14)
    
    def _generate_stats_text(self, df: pd.DataFrame) -> str:
        """Generate statistics text."""
        closed_trades = df[df['action'] == 'close'].copy()
        
        if closed_trades.empty:
            return "No closed trades yet"
        
        # Calculate metrics
        winning_trades = closed_trades[closed_trades['pnl'] > 0]
        losing_trades = closed_trades[closed_trades['pnl'] < 0]
        
        total_trades = len(closed_trades)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        total_pnl = closed_trades['pnl'].sum()
        avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
        
        # Latest balance
        last_balance = df['balance_after'].iloc[-1] if 'balance_after' in df.columns else 0
        
        # Profit factor
        total_wins = winning_trades['pnl'].sum() if not winning_trades.empty else 0
        total_losses = abs(losing_trades['pnl'].sum()) if not losing_trades.empty else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Format statistics
        stats_text = f"""
╔═══════════════════════════════╗
║      TRADING STATISTICS       ║
╠═══════════════════════════════╣
║ Total Trades  : {total_trades:>13} ║
║ Win Rate      : {win_rate:>11.1f}% ║
║ Total PnL     : ${total_pnl:>11.2f} ║
║ Average Win   : ${avg_win:>11.2f} ║
║ Average Loss  : ${avg_loss:>11.2f} ║
║ Profit Factor : {profit_factor:>11.2f}x ║
╠═══════════════════════════════╣
║ Balance       : ${last_balance:>11.2f} ║
║ Updated       : {datetime.now().strftime('%H:%M:%S'):>13} ║
╚═══════════════════════════════╝
"""
        return stats_text
    
    def start(self, interval: int = 5000):
        """Start dashboard with auto-refresh."""
        print("Starting Trading Dashboard...")
        print("Press Ctrl+C to stop")
        
        # Animation
        ani = FuncAnimation(self.fig, self.update_plots, 
                          interval=interval, 
                          cache_frame_data=False)
        
        plt.show()


if __name__ == "__main__":
    dashboard = TradingDashboard()
    dashboard.start()