# live_dashboard.py
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime
import numpy as np
import os

class LiveDashboard:
    def __init__(self, csv_file='trading_history.csv'):
        self.csv_file = csv_file
        self.fig, self.axes = plt.subplots(2, 2, figsize=(15, 10))
        self.fig.suptitle('Live Trading Dashboard', fontsize=16)
        
        # Ustaw styl
        plt.style.use('dark_background')
        
        # Kolory
        self.green = '#00ff00'
        self.red = '#ff0000'
        self.blue = '#00ffff'
        self.yellow = '#ffff00'
        
    def update_plots(self, frame):
        """Aktualizuje wykresy"""
        try:
            # Sprawdź czy plik istnieje
            if not os.path.exists(self.csv_file):
                self.show_waiting_message()
                return
            
            # Wczytaj dane
            df = pd.read_csv(self.csv_file)
            if df.empty:
                self.show_waiting_message()
                return
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Wyczyść wykresy
            for ax in self.axes.flat:
                ax.clear()
            
            # Ustaw style dla każdego wykresu
            for ax in self.axes.flat:
                ax.set_facecolor('#0d0d0d')
                ax.grid(True, alpha=0.2, color='gray')
            
            # Wykres 1: PnL w czasie
            self.plot_cumulative_pnl(df)
            
            # Wykres 2: Saldo konta
            self.plot_account_balance(df)
            
            # Wykres 3: Rozkład PnL
            self.plot_pnl_distribution(df)
            
            # Wykres 4: Statystyki
            self.plot_statistics(df)
            
            plt.tight_layout()
            
        except Exception as e:
            print(f"Error updating dashboard: {e}")
    
    def show_waiting_message(self):
        """Pokazuje komunikat o oczekiwaniu na dane"""
        for ax in self.axes.flat:
            ax.clear()
            ax.text(0.5, 0.5, 'Waiting for trading data...', 
                   transform=ax.transAxes, 
                   ha='center', va='center', 
                   fontsize=16, color=self.yellow)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
    
    def plot_cumulative_pnl(self, df):
        """Wykres skumulowanego PnL"""
        ax = self.axes[0, 0]
        closed_trades = df[df['action'] == 'close'].copy()
        
        if not closed_trades.empty:
            closed_trades['cumulative_pnl'] = closed_trades['pnl'].cumsum()
            
            # Kolor linii w zależności od ostatniego PnL
            color = self.green if closed_trades['cumulative_pnl'].iloc[-1] >= 0 else self.red
            
            ax.plot(closed_trades['timestamp'], closed_trades['cumulative_pnl'], 
                   color=color, linewidth=2)
            
            # Wypełnij obszar
            ax.fill_between(closed_trades['timestamp'], 0, closed_trades['cumulative_pnl'], 
                           color=color, alpha=0.3)
            
            # Dodaj wartość końcową
            last_pnl = closed_trades['cumulative_pnl'].iloc[-1]
            ax.text(0.98, 0.98, f'${last_pnl:.2f}', 
                   transform=ax.transAxes, 
                   ha='right', va='top', 
                   fontsize=14, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
        
        ax.set_title('Cumulative PnL', fontsize=14, color='white')
        ax.set_ylabel('PnL (USDT)', color='white')
        ax.tick_params(colors='white')
    
    def plot_account_balance(self, df):
        """Wykres salda konta"""
        ax = self.axes[0, 1]
        
        if 'balance_after' in df.columns:
            # Filtruj tylko wartości różne od 0
            balance_data = df[df['balance_after'] > 0].copy()
            
            if not balance_data.empty:
                ax.plot(balance_data['timestamp'], balance_data['balance_after'], 
                       color=self.blue, linewidth=2)
                
                # Dodaj początkowe i końcowe saldo
                start_balance = balance_data['balance_after'].iloc[0]
                end_balance = balance_data['balance_after'].iloc[-1]
                
                # Procent zmiany
                pct_change = ((end_balance - start_balance) / start_balance) * 100
                color = self.green if pct_change >= 0 else self.red
                
                ax.text(0.98, 0.98, f'${end_balance:.2f}\n({pct_change:+.1f}%)', 
                       transform=ax.transAxes, 
                       ha='right', va='top', 
                       fontsize=14, fontweight='bold',
                       bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
        
        ax.set_title('Account Balance', fontsize=14, color='white')
        ax.set_ylabel('Balance (USDT)', color='white')
        ax.tick_params(colors='white')
    
    def plot_pnl_distribution(self, df):
        """Wykres rozkładu PnL"""
        ax = self.axes[1, 0]
        closed_trades = df[df['action'] == 'close'].copy()
        
        if not closed_trades.empty:
            # Rozdziel na zyski i straty
            profits = closed_trades[closed_trades['pnl'] > 0]['pnl']
            losses = closed_trades[closed_trades['pnl'] < 0]['pnl']
            
            # Histogram
            if not profits.empty:
                ax.hist(profits, bins=15, color=self.green, alpha=0.6, label='Profits')
            if not losses.empty:
                ax.hist(losses, bins=15, color=self.red, alpha=0.6, label='Losses')
            
            ax.axvline(x=0, color='white', linestyle='--', alpha=0.5)
            ax.legend()
            
            # Średnia
            avg_pnl = closed_trades['pnl'].mean()
            ax.axvline(x=avg_pnl, color=self.yellow, linestyle='-', linewidth=2)
            ax.text(avg_pnl, ax.get_ylim()[1]*0.9, f'Avg: ${avg_pnl:.2f}', 
                   ha='center', color=self.yellow, fontweight='bold')
        
        ax.set_title('PnL Distribution', fontsize=14, color='white')
        ax.set_xlabel('PnL (USDT)', color='white')
        ax.set_ylabel('Frequency', color='white')
        ax.tick_params(colors='white')
    
    def plot_statistics(self, df):
        """Wykres statystyk"""
        ax = self.axes[1, 1]
        ax.axis('off')
        
        stats_text = self.generate_stats_text(df)
        
        # Tło dla statystyk
        ax.add_patch(plt.Rectangle((0.05, 0.05), 0.9, 0.9, 
                                 facecolor='#1a1a1a', 
                                 edgecolor=self.blue, 
                                 linewidth=2))
        
        ax.text(0.5, 0.5, stats_text, 
               transform=ax.transAxes,
               ha='center', va='center',
               fontsize=12, 
               color='white',
               family='monospace')
        
        ax.set_title('Trading Statistics', fontsize=14, color='white')
    
    def generate_stats_text(self, df):
        """Generuje tekst ze statystykami"""
        closed_trades = df[df['action'] == 'close'].copy()
        
        if closed_trades.empty:
            return "No closed trades yet"
        
        winning_trades = closed_trades[closed_trades['pnl'] > 0]
        losing_trades = closed_trades[closed_trades['pnl'] < 0]
        
        total_trades = len(closed_trades)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        total_pnl = closed_trades['pnl'].sum()
        avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
        
        # Ostatnie saldo
        last_balance = df['balance_after'].iloc[-1] if 'balance_after' in df.columns else 0
        
        # Profit factor
        total_wins = winning_trades['pnl'].sum() if not winning_trades.empty else 0
        total_losses = abs(losing_trades['pnl'].sum()) if not losing_trades.empty else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Najlepsza i najgorsza transakcja
        best_trade = closed_trades['pnl'].max()
        worst_trade = closed_trades['pnl'].min()
        
        # Kolorowanie wartości
        def colorize(value, is_currency=True):
            if is_currency:
                formatted = f"${value:.2f}"
            else:
                formatted = f"{value:.1f}%" if abs(value) < 100 else f"{value:.0f}"
            
            if value > 0:
                return f"[+] {formatted}"
            elif value < 0:
                return f"[-] {formatted}"
            else:
                return f"    {formatted}"
        
        stats_text = f"""
╔════════════════════════════════════╗
║         TRADING STATISTICS         ║
╠════════════════════════════════════╣
║ Total Trades      : {total_trades:>14} ║
║ Winning Trades    : {len(winning_trades):>14} ║
║ Losing Trades     : {len(losing_trades):>14} ║
║ Win Rate          : {win_rate:>13.1f}% ║
╠════════════════════════════════════╣
║ Total PnL         : {colorize(total_pnl):>14} ║
║ Average Win       : {colorize(avg_win):>14} ║
║ Average Loss      : {colorize(avg_loss):>14} ║
║ Best Trade        : {colorize(best_trade):>14} ║
║ Worst Trade       : {colorize(worst_trade):>14} ║
║ Profit Factor     : {profit_factor:>13.2f}x ║
╠════════════════════════════════════╣
║ Current Balance   : {f"${last_balance:.2f}":>14} ║
║ Last Update       : {datetime.now().strftime('%H:%M:%S'):>14} ║
╚════════════════════════════════════╝
"""
        return stats_text
    
    def start(self, interval=5000):
        """Uruchom dashboard z automatycznym odświeżaniem"""
        print("Starting Live Dashboard...")
        print("Press Ctrl+C to stop")
        
        # Animacja
        ani = FuncAnimation(self.fig, self.update_plots, 
                          interval=interval, 
                          cache_frame_data=False)
        
        # Pokaż wykres
        plt.show()

if __name__ == "__main__":
    dashboard = LiveDashboard()
    dashboard.start()