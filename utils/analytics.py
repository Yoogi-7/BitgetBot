# utils/analytics.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, Optional


class TradingAnalytics:
    """Simplified trading analytics and reporting."""
    
    def __init__(self, csv_file: str = 'trading_history.csv'):
        self.csv_file = csv_file
        self.df = None
        self._load_data()
    
    def _load_data(self):
        """Load trading data from CSV."""
        try:
            self.df = pd.read_csv(self.csv_file)
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
            print(f"Loaded {len(self.df)} records")
        except Exception as e:
            print(f"Error loading data: {e}")
            self.df = pd.DataFrame()
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        if self.df.empty:
            return {}
        
        closed_trades = self.df[self.df['action'] == 'close']
        if closed_trades.empty:
            return {}
        
        # Calculate metrics
        metrics = self._calculate_metrics(closed_trades)
        
        # Generate visualizations
        self._create_visualizations(closed_trades)
        
        # Save report
        self._save_report(metrics)
        
        return metrics
    
    def _calculate_metrics(self, closed_trades: pd.DataFrame) -> Dict:
        """Calculate trading metrics."""
        total_trades = len(closed_trades)
        winning_trades = closed_trades[closed_trades['pnl'] > 0]
        losing_trades = closed_trades[closed_trades['pnl'] < 0]
        
        # Basic metrics
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        total_pnl = closed_trades['pnl'].sum()
        avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
        
        # Advanced metrics
        profit_factor = (
            winning_trades['pnl'].sum() / abs(losing_trades['pnl'].sum()) 
            if not losing_trades.empty else 0
        )
        
        # Sharpe ratio (simplified)
        returns = closed_trades['pnl'].pct_change().dropna()
        sharpe_ratio = (
            np.sqrt(252) * (returns.mean() / returns.std()) 
            if returns.std() != 0 else 0
        )
        
        # Maximum drawdown
        cum_pnl = closed_trades['pnl'].cumsum()
        peak = cum_pnl.cummax()
        drawdown = cum_pnl - peak
        max_drawdown = drawdown.min()
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'best_trade': closed_trades['pnl'].max(),
            'worst_trade': closed_trades['pnl'].min()
        }
    
    def _create_visualizations(self, closed_trades: pd.DataFrame):
        """Create performance visualizations."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Trading Performance Analysis', fontsize=16)
        
        # Cumulative PnL
        closed_trades['cumulative_pnl'] = closed_trades['pnl'].cumsum()
        axes[0, 0].plot(closed_trades['timestamp'], closed_trades['cumulative_pnl'])
        axes[0, 0].set_title('Cumulative PnL')
        axes[0, 0].set_ylabel('PnL (USDT)')
        axes[0, 0].grid(True)
        
        # PnL distribution
        axes[0, 1].hist(closed_trades['pnl'], bins=30, edgecolor='black')
        axes[0, 1].axvline(0, color='red', linestyle='--')
        axes[0, 1].set_title('PnL Distribution')
        axes[0, 1].set_xlabel('PnL (USDT)')
        axes[0, 1].set_ylabel('Frequency')
        
        # Win/Loss by hour
        closed_trades['hour'] = closed_trades['timestamp'].dt.hour
        hourly_pnl = closed_trades.groupby('hour')['pnl'].sum()
        axes[1, 0].bar(hourly_pnl.index, hourly_pnl.values)
        axes[1, 0].set_title('PnL by Hour')
        axes[1, 0].set_xlabel('Hour')
        axes[1, 0].set_ylabel('Total PnL')
        
        # Strategy performance
        if 'reason' in closed_trades.columns:
            strategy_pnl = closed_trades.groupby('reason')['pnl'].agg(['sum', 'count', 'mean'])
            strategy_pnl = strategy_pnl.sort_values('sum', ascending=True)
            
            axes[1, 1].barh(range(len(strategy_pnl)), strategy_pnl['sum'])
            axes[1, 1].set_yticks(range(len(strategy_pnl)))
            axes[1, 1].set_yticklabels(strategy_pnl.index)
            axes[1, 1].set_title('PnL by Strategy')
            axes[1, 1].set_xlabel('Total PnL')
        
        plt.tight_layout()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        plt.savefig(f'performance_report_{timestamp}.png')
        plt.close()
    
    def _save_report(self, metrics: Dict):
        """Save performance report to file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'performance_report_{timestamp}.txt'
        
        with open(report_file, 'w') as f:
            f.write("TRADING PERFORMANCE REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("PERFORMANCE METRICS:\n")
            f.write(f"Total Trades: {metrics['total_trades']}\n")
            f.write(f"Win Rate: {metrics['win_rate']:.1f}%\n")
            f.write(f"Total PnL: ${metrics['total_pnl']:.2f}\n")
            f.write(f"Average Win: ${metrics['avg_win']:.2f}\n")
            f.write(f"Average Loss: ${metrics['avg_loss']:.2f}\n")
            f.write(f"Profit Factor: {metrics['profit_factor']:.2f}\n")
            f.write(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n")
            f.write(f"Max Drawdown: ${metrics['max_drawdown']:.2f}\n")
            f.write(f"Best Trade: ${metrics['best_trade']:.2f}\n")
            f.write(f"Worst Trade: ${metrics['worst_trade']:.2f}\n")
        
        print(f"Report saved to: {report_file}")


if __name__ == "__main__":
    analytics = TradingAnalytics()
    analytics.generate_performance_report()