# advanced_analytics.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from scipy import stats

class AdvancedAnalytics:
    def __init__(self, csv_file='trading_history.csv'):
        self.csv_file = csv_file
        self.df = None
        self.load_data()
    
    def load_data(self):
        """Wczytuje dane z CSV"""
        try:
            self.df = pd.read_csv(self.csv_file)
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
            print(f"Loaded {len(self.df)} records")
        except Exception as e:
            print(f"Error loading data: {e}")
            self.df = pd.DataFrame()
    
    def performance_metrics(self):
        """Oblicza zaawansowane metryki wydajności"""
        if self.df.empty:
            print("No data available")
            return
        
        closed_trades = self.df[self.df['action'] == 'close']
        if closed_trades.empty:
            print("No closed trades found")
            return
        
# Podstawowe metryki
        total_trades = len(closed_trades)
        profitable_trades = closed_trades[closed_trades['pnl'] > 0]
        losing_trades = closed_trades[closed_trades['pnl'] < 0]
        
        # Współczynniki
        win_rate = len(profitable_trades) / total_trades * 100
        avg_win = profitable_trades['pnl'].mean() if not profitable_trades.empty else 0
        avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
        
        # Expectancy
        expectancy = (win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss)
        
        # Profit Factor
        total_profit = profitable_trades['pnl'].sum() if not profitable_trades.empty else 0
        total_loss = abs(losing_trades['pnl'].sum()) if not losing_trades.empty else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # Recovery Factor
        max_dd = self.calculate_max_drawdown(closed_trades)
        recovery_factor = closed_trades['pnl'].sum() / abs(max_dd) if max_dd != 0 else 0
        
        # Sharpe Ratio
        returns = closed_trades['pnl'].pct_change().dropna()
        sharpe_ratio = np.sqrt(252) * (returns.mean() / returns.std()) if returns.std() != 0 else 0
        
        # Calmar Ratio
        annual_return = closed_trades['pnl'].sum() * (365 / (closed_trades['timestamp'].max() - closed_trades['timestamp'].min()).days)
        calmar_ratio = annual_return / abs(max_dd) if max_dd != 0 else 0
        
        # Time metrics
        closed_trades['duration'] = pd.to_datetime(closed_trades['timestamp']) - pd.to_datetime(closed_trades['timestamp'].shift(1))
        avg_trade_duration = closed_trades['duration'].mean()
        
        print("\n" + "="*50)
        print("         ADVANCED METRICS")
        print("="*50)
        print(f"Total Trades:       {total_trades}")
        print(f"Win Rate:           {win_rate:.1f}%")
        print(f"Expectancy:         ${expectancy:.2f}")
        print(f"Profit Factor:      {profit_factor:.2f}")
        print(f"Recovery Factor:    {recovery_factor:.2f}")
        print(f"Sharpe Ratio:       {sharpe_ratio:.2f}")
        print(f"Calmar Ratio:       {calmar_ratio:.2f}")
        print(f"Avg Trade Duration: {avg_trade_duration}")
        print("="*50)
        
        return {
            'win_rate': win_rate,
            'expectancy': expectancy,
            'profit_factor': profit_factor,
            'recovery_factor': recovery_factor,
            'sharpe_ratio': sharpe_ratio,
            'calmar_ratio': calmar_ratio
        }
    
    def calculate_max_drawdown(self, trades_df):
        """Oblicza maksymalny drawdown"""
        trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
        trades_df['peak'] = trades_df['cumulative_pnl'].cummax()
        trades_df['drawdown'] = trades_df['cumulative_pnl'] - trades_df['peak']
        return trades_df['drawdown'].min()
    
    def analyze_by_time(self):
        """Analiza wyników według czasu"""
        closed_trades = self.df[self.df['action'] == 'close']
        if closed_trades.empty:
            return
        
        # Dodaj komponenty czasowe
        closed_trades['hour'] = closed_trades['timestamp'].dt.hour
        closed_trades['day_of_week'] = closed_trades['timestamp'].dt.dayofweek
        closed_trades['day_of_month'] = closed_trades['timestamp'].dt.day
        
        # Analiza godzinowa
        hourly_stats = closed_trades.groupby('hour').agg({
            'pnl': ['count', 'sum', 'mean']
        })
        
        # Wizualizacja
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # PnL po godzinach
        axes[0, 0].bar(hourly_stats.index, hourly_stats['pnl']['sum'])
        axes[0, 0].set_title('PnL by Hour')
        axes[0, 0].set_xlabel('Hour')
        axes[0, 0].set_ylabel('Total PnL')
        
        # Liczba transakcji po godzinach
        axes[0, 1].bar(hourly_stats.index, hourly_stats['pnl']['count'])
        axes[0, 1].set_title('Number of Trades by Hour')
        axes[0, 1].set_xlabel('Hour')
        axes[0, 1].set_ylabel('Count')
        
        # PnL po dniach tygodnia
        daily_stats = closed_trades.groupby('day_of_week')['pnl'].sum()
        days_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        axes[1, 0].bar(range(7), daily_stats.reindex(range(7), fill_value=0))
        axes[1, 0].set_xticks(range(7))
        axes[1, 0].set_xticklabels(days_names)
        axes[1, 0].set_title('PnL by Day of Week')
        axes[1, 0].set_ylabel('Total PnL')
        
        # Średni PnL po godzinach
        axes[1, 1].bar(hourly_stats.index, hourly_stats['pnl']['mean'])
        axes[1, 1].set_title('Average PnL by Hour')
        axes[1, 1].set_xlabel('Hour')
        axes[1, 1].set_ylabel('Average PnL')
        
        plt.tight_layout()
        plt.savefig('time_analysis.png')
        plt.show()
    
    def analyze_by_market_conditions(self):
        """Analiza według warunków rynkowych"""
        if 'rsi' not in self.df.columns or 'trend' not in self.df.columns:
            print("Market condition data not available")
            return
        
        closed_trades = self.df[self.df['action'] == 'close']
        
        # Analiza według trendu
        trend_stats = closed_trades.groupby('trend').agg({
            'pnl': ['count', 'sum', 'mean'],
            'side': lambda x: x.value_counts().to_dict()
        })
        
        # Analiza według RSI
        closed_trades['rsi_range'] = pd.cut(closed_trades['rsi'], 
                                          bins=[0, 30, 50, 70, 100],
                                          labels=['Oversold', 'Neutral Low', 'Neutral High', 'Overbought'])
        
        rsi_stats = closed_trades.groupby('rsi_range').agg({
            'pnl': ['count', 'sum', 'mean']
        })
        
        # Wizualizacja
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # PnL według trendu
        axes[0, 0].bar(trend_stats.index, trend_stats['pnl']['sum'])
        axes[0, 0].set_title('PnL by Market Trend')
        axes[0, 0].set_ylabel('Total PnL')
        
        # Win rate według trendu
        win_rates = []
        for trend in trend_stats.index:
            trend_trades = closed_trades[closed_trades['trend'] == trend]
            wins = len(trend_trades[trend_trades['pnl'] > 0])
            total = len(trend_trades)
            win_rate = wins / total * 100 if total > 0 else 0
            win_rates.append(win_rate)
        
        axes[0, 1].bar(trend_stats.index, win_rates)
        axes[0, 1].set_title('Win Rate by Trend')
        axes[0, 1].set_ylabel('Win Rate %')
        
        # PnL według RSI
        axes[1, 0].bar(rsi_stats.index, rsi_stats['pnl']['sum'])
        axes[1, 0].set_title('PnL by RSI Range')
        axes[1, 0].set_ylabel('Total PnL')
        
        # Średni PnL według RSI
        axes[1, 1].bar(rsi_stats.index, rsi_stats['pnl']['mean'])
        axes[1, 1].set_title('Average PnL by RSI Range')
        axes[1, 1].set_ylabel('Average PnL')
        
        plt.tight_layout()
        plt.savefig('market_conditions_analysis.png')
        plt.show()
    
    def trade_distribution_analysis(self):
        """Analiza rozkładu transakcji"""
        closed_trades = self.df[self.df['action'] == 'close']
        if closed_trades.empty:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Histogram PnL
        axes[0, 0].hist(closed_trades['pnl'], bins=30, edgecolor='black')
        axes[0, 0].axvline(0, color='red', linestyle='--')
        axes[0, 0].set_title('PnL Distribution')
        axes[0, 0].set_xlabel('PnL')
        axes[0, 0].set_ylabel('Frequency')
        
        # Q-Q plot
        stats.probplot(closed_trades['pnl'], dist="norm", plot=axes[0, 1])
        axes[0, 1].set_title('Q-Q Plot (Normal Distribution)')
        
        # Box plot według strategii
        if 'reason' in closed_trades.columns:
            reason_groups = closed_trades.groupby('reason')['pnl'].apply(list)
            axes[1, 0].boxplot(reason_groups.values, labels=reason_groups.index)
            axes[1, 0].set_title('PnL Distribution by Strategy')
            axes[1, 0].set_ylabel('PnL')
            plt.setp(axes[1, 0].xaxis.get_majorticklabels(), rotation=45)
        
        # Scatter plot: Trade size vs PnL
        if 'size_usd' in closed_trades.columns:
            axes[1, 1].scatter(closed_trades['size_usd'], closed_trades['pnl'], alpha=0.6)
            axes[1, 1].set_title('Trade Size vs PnL')
            axes[1, 1].set_xlabel('Trade Size (USD)')
            axes[1, 1].set_ylabel('PnL')
            axes[1, 1].axhline(0, color='red', linestyle='--')
        
        plt.tight_layout()
        plt.savefig('trade_distribution_analysis.png')
        plt.show()
    
    def correlation_analysis(self):
        """Analiza korelacji między zmiennymi"""
        # Przygotuj dane
        analysis_df = self.df.copy()
        
        # Dodaj kolumny techniczne jeśli nie istnieją
        if 'rsi' not in analysis_df.columns:
            print("Technical indicators not available for correlation analysis")
            return
        
        # Wybierz tylko numeryczne kolumny
        numeric_cols = ['price', 'size_usd', 'pnl', 'rsi']
        correlation_data = analysis_df[analysis_df['action'] == 'close'][numeric_cols]
        
        # Oblicz macierz korelacji
        corr_matrix = correlation_data.corr()
        
        # Wizualizacja
        plt.figure(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0)
        plt.title('Correlation Matrix')
        plt.tight_layout()
        plt.savefig('correlation_analysis.png')
        plt.show()
    
    def generate_report(self):
        """Generuje kompletny raport"""
        print("\n" + "="*50)
        print("    COMPREHENSIVE TRADING ANALYSIS REPORT")
        print("="*50)
        
        # Performance metrics
        metrics = self.performance_metrics()
        
        # Time analysis
        print("\nGenerating time analysis...")
        self.analyze_by_time()
        
        # Market conditions analysis
        print("\nGenerating market conditions analysis...")
        self.analyze_by_market_conditions()
        
        # Trade distribution
        print("\nGenerating trade distribution analysis...")
        self.trade_distribution_analysis()
        
        # Correlation analysis
        print("\nGenerating correlation analysis...")
        self.correlation_analysis()
        
        # Save summary
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'analysis_report_{timestamp}.txt', 'w') as f:
            f.write("TRADING ANALYSIS REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("="*50 + "\n\n")
            
            f.write("PERFORMANCE METRICS:\n")
            for key, value in metrics.items():
                f.write(f"{key}: {value}\n")
            
            f.write("\n\nFILES GENERATED:\n")
            f.write("- time_analysis.png\n")
            f.write("- market_conditions_analysis.png\n")
            f.write("- trade_distribution_analysis.png\n")
            f.write("- correlation_analysis.png\n")
        
        print(f"\nReport saved as: analysis_report_{timestamp}.txt")

if __name__ == "__main__":
    analyzer = AdvancedAnalytics()
    analyzer.generate_report()