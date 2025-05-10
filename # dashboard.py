# dashboard.py
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

def generate_report(csv_file='trading_history.csv'):
    """Generuje raport z wyników tradingu"""
    
    if not os.path.exists(csv_file):
        print(f"Brak pliku {csv_file}. Uruchom bota najpierw.")
        return
    
    # Wczytaj dane
    df = pd.read_csv(csv_file)
    
    if df.empty:
        print("Brak transakcji do analizy")
        return
    
    # Konwertuj timestamp do datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Podstawowe statystyki
    total_trades = len(df)
    closed_trades = df[df['action'] == 'close']
    
    if not closed_trades.empty:
        winning_trades = closed_trades[closed_trades['pnl'] > 0]
        losing_trades = closed_trades[closed_trades['pnl'] < 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100
        total_pnl = closed_trades['pnl'].sum()
        avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
        
        print(f"\n=== Trading Report ===")
        print(f"Total trades: {total_trades}")
        print(f"Closed trades: {len(closed_trades)}")
        print(f"Win rate: {win_rate:.2f}%")
        print(f"Total PnL: ${total_pnl:.2f}")
        print(f"Average win: ${avg_win:.2f}")
        print(f"Average loss: ${avg_loss:.2f}")
        
        # Wykres PnL
        plt.figure(figsize=(12, 6))
        
        # Skumulowany PnL
        closed_trades = closed_trades.sort_values('timestamp')
        closed_trades['cumulative_pnl'] = closed_trades['pnl'].cumsum()
        
        plt.subplot(2, 1, 1)
        plt.plot(closed_trades['timestamp'], closed_trades['cumulative_pnl'], marker='o')
        plt.title('Cumulative PnL')
        plt.ylabel('PnL (USDT)')
        plt.grid(True)
        
        # Histogram PnL
        plt.subplot(2, 1, 2)
        plt.hist(closed_trades['pnl'], bins=20, edgecolor='black')
        plt.title('PnL Distribution')
        plt.xlabel('PnL (USDT)')
        plt.ylabel('Frequency')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'trading_report_{datetime.now().strftime("%Y%m%d")}.png')
        plt.show()
        
        # Analiza po strategiach
        print("\n=== Analysis by Reason ===")
        reason_stats = closed_trades.groupby('reason').agg({
            'pnl': ['count', 'sum', 'mean'],
            'side': 'first'
        })
        print(reason_stats)
        
        # Analiza po trendzie
        if 'trend' in closed_trades.columns:
            print("\n=== Analysis by Trend ===")
            trend_stats = closed_trades.groupby('trend').agg({
                'pnl': ['count', 'sum', 'mean']
            })
            print(trend_stats)
        
        # Najlepsze i najgorsze transakcje
        print("\n=== Best Trades ===")
        print(closed_trades.nlargest(3, 'pnl')[['timestamp', 'side', 'pnl', 'reason']])
        
        print("\n=== Worst Trades ===")
        print(closed_trades.nsmallest(3, 'pnl')[['timestamp', 'side', 'pnl', 'reason']])
    
    else:
        print("Brak zamkniętych transakcji do analizy")

if __name__ == "__main__":
    generate_report()