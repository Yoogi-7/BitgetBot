# backtest.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from src.data_collector import DataCollector
from src.strategies import FuturesStrategy
from config.settings import Config

class BacktestEngine:
    def __init__(self):
        self.data_collector = DataCollector()
        self.strategy = FuturesStrategy()
        self.initial_balance = 1000.0
        self.leverage = Config.LEVERAGE
        
        # Tracking
        self.trades = []
        self.balance_history = []
        self.positions = []
        
    def run_backtest(self, days=30, timeframe='5m'):
        """Uruchamia backtest na danych historycznych"""
        print(f"Starting backtest for {days} days on {timeframe} timeframe...")
        
        # Pobierz dane historyczne
        limit = self._calculate_candles(days, timeframe)
        df = self.data_collector.get_ohlcv_data(
            symbol=Config.TRADING_SYMBOL,
            timeframe=timeframe,
            limit=limit
        )
        
        if df is None or df.empty:
            print("Error: No data received")
            return
        
        print(f"Loaded {len(df)} candles")
        
        # Inicjalizacja
        balance = self.initial_balance
        position = None
        
        # Symulacja
        for i in range(100, len(df)):
            current_data = df.iloc[:i+1].copy()
            current_price = current_data.iloc[-1]['close']
            current_time = current_data.iloc[-1]['timestamp']
            
            # Update position P&L
            if position:
                if position['side'] == 'long':
                    position['unrealized_pnl'] = (current_price - position['entry_price']) * position['size']
                else:
                    position['unrealized_pnl'] = (position['entry_price'] - current_price) * position['size']
                
                position['mark_price'] = current_price
            
            # Generuj sygnał
            existing_positions = [position] if position else []
            signal = self.strategy.generate_signal(current_data, existing_positions)
            
            # Zarządzanie pozycją
            if position:
                # Check stop loss / take profit
                should_close = False
                close_reason = ""
                
                if position['side'] == 'long':
                    if current_price <= position['entry_price'] * (1 - Config.STOP_LOSS_PERCENT/100):
                        should_close = True
                        close_reason = "Stop loss hit"
                    elif current_price >= position['entry_price'] * (1 + Config.TAKE_PROFIT_PERCENT/100):
                        should_close = True
                        close_reason = "Take profit hit"
                else:  # short
                    if current_price >= position['entry_price'] * (1 + Config.STOP_LOSS_PERCENT/100):
                        should_close = True
                        close_reason = "Stop loss hit"
                    elif current_price <= position['entry_price'] * (1 - Config.TAKE_PROFIT_PERCENT/100):
                        should_close = True
                        close_reason = "Take profit hit"
                
                # Close from signal
                if signal['action'] == 'CLOSE' and signal['side'] == position['side']:
                    should_close = True
                    close_reason = signal['reason']
                
                if should_close:
                    # Zamknij pozycję
                    pnl = position['unrealized_pnl']
                    balance += position['size_usd'] + pnl
                    
                    self.trades.append({
                        'timestamp': current_time,
                        'action': 'close',
                        'side': position['side'],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'size_usd': position['size_usd'],
                        'pnl': pnl,
                        'reason': close_reason,
                        'balance_after': balance
                    })
                    
                    position = None
            
            # Otwórz nową pozycję
            if signal['action'] == 'OPEN' and signal['confidence'] >= 0.7 and not position:
                size_usd = min(Config.TRADE_AMOUNT_USDT, balance * 0.95)
                
                if size_usd >= 10:  # Minimum trade size
                    position = {
                        'side': signal['side'],
                        'entry_price': current_price,
                        'mark_price': current_price,
                        'size': size_usd / current_price,
                        'size_usd': size_usd,
                        'unrealized_pnl': 0,
                        'opened_at': current_time
                    }
                    
                    balance -= size_usd
                    
                    self.trades.append({
                        'timestamp': current_time,
                        'action': 'open',
                        'side': signal['side'],
                        'entry_price': current_price,
                        'size_usd': size_usd,
                        'reason': signal['reason'],
                        'balance_after': balance
                    })
            
            # Zapisz stan balansu
            self.balance_history.append({
                'timestamp': current_time,
                'balance': balance + (position['size_usd'] + position['unrealized_pnl'] if position else 0),
                'equity': balance,
                'unrealized_pnl': position['unrealized_pnl'] if position else 0
            })
        
        # Zamknij ostatnią pozycję jeśli otwarta
        if position:
            pnl = position['unrealized_pnl']
            balance += position['size_usd'] + pnl
            
            self.trades.append({
                'timestamp': current_time,
                'action': 'close',
                'side': position['side'],
                'entry_price': position['entry_price'],
                'exit_price': current_price,
                'size_usd': position['size_usd'],
                'pnl': pnl,
                'reason': 'Backtest end',
                'balance_after': balance
            })
        
        return self.generate_report()
    
    def _calculate_candles(self, days, timeframe):
        """Oblicza ilość świeczek potrzebnych"""
        minutes_per_candle = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        
        if timeframe not in minutes_per_candle:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        candles_per_day = 1440 / minutes_per_candle[timeframe]
        total_candles = int(candles_per_day * days)
        
        # Limit API
        return min(total_candles, 1000)
    
    def generate_report(self):
        """Generuje raport z backtestingu"""
        if not self.trades:
            print("No trades executed during backtest")
            return None
        
        trades_df = pd.DataFrame(self.trades)
        balance_df = pd.DataFrame(self.balance_history)
        
        # Oblicz statystyki
        closed_trades = trades_df[trades_df['action'] == 'close']
        
        if closed_trades.empty:
            print("No closed trades in backtest")
            return None
        
        # Podstawowe metryki
        total_trades = len(closed_trades)
        winning_trades = closed_trades[closed_trades['pnl'] > 0]
        losing_trades = closed_trades[closed_trades['pnl'] < 0]
        
        win_rate = len(winning_trades) / total_trades * 100
        total_pnl = closed_trades['pnl'].sum()
        avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
        
        # Profit factor
        total_wins = winning_trades['pnl'].sum() if not winning_trades.empty else 0
        total_losses = abs(losing_trades['pnl'].sum()) if not losing_trades.empty else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Maximum drawdown
        balance_df['peak'] = balance_df['balance'].cummax()
        balance_df['drawdown'] = balance_df['balance'] - balance_df['peak']
        max_drawdown = balance_df['drawdown'].min()
        max_drawdown_pct = (max_drawdown / balance_df['peak'].max()) * 100
        
        # Return metrics
        total_return = (balance_df['balance'].iloc[-1] - self.initial_balance) / self.initial_balance * 100
        
        # Print report
        print("\n" + "="*50)
        print("           BACKTEST RESULTS")
        print("="*50)
        print(f"Initial Balance:    ${self.initial_balance:.2f}")
        print(f"Final Balance:      ${balance_df['balance'].iloc[-1]:.2f}")
        print(f"Total Return:       {total_return:.2f}%")
        print(f"Total PnL:          ${total_pnl:.2f}")
        print("-"*50)
        print(f"Total Trades:       {total_trades}")
        print(f"Winning Trades:     {len(winning_trades)}")
        print(f"Losing Trades:      {len(losing_trades)}")
        print(f"Win Rate:           {win_rate:.1f}%")
        print("-"*50)
        print(f"Average Win:        ${avg_win:.2f}")
        print(f"Average Loss:       ${avg_loss:.2f}")
        print(f"Profit Factor:      {profit_factor:.2f}")
        print(f"Max Drawdown:       ${max_drawdown:.2f} ({max_drawdown_pct:.1f}%)")
        print("="*50)
        
        # Wizualizacja
        self.plot_results(balance_df, trades_df)
        
        return {
            'trades': trades_df,
            'balance_history': balance_df,
            'metrics': {
                'total_return': total_return,
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct
            }
        }
    
    def plot_results(self, balance_df, trades_df):
        """Tworzy wykresy z wynikami"""
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))
        
        # Wykres 1: Balance
        axes[0].plot(balance_df['timestamp'], balance_df['balance'], 'b-', linewidth=2)
        axes[0].fill_between(balance_df['timestamp'], balance_df['balance'], 
                           self.initial_balance, alpha=0.3)
        axes[0].set_title('Account Balance Over Time')
        axes[0].set_ylabel('Balance (USDT)')
        axes[0].grid(True)
        
        # Zaznacz trades
        for _, trade in trades_df[trades_df['action'] == 'open'].iterrows():
            marker = '^' if trade['side'] == 'long' else 'v'
            color = 'g' if trade['side'] == 'long' else 'r'
            axes[0].scatter(trade['timestamp'], trade['balance_after'], 
                          marker=marker, color=color, s=100)
        
        # Wykres 2: Drawdown
        axes[1].fill_between(balance_df['timestamp'], 0, balance_df['drawdown'], 
                           color='red', alpha=0.3)
        axes[1].plot(balance_df['timestamp'], balance_df['drawdown'], 'r-', linewidth=2)
        axes[1].set_title('Drawdown')
        axes[1].set_ylabel('Drawdown (USDT)')
        axes[1].grid(True)
        
        # Wykres 3: PnL Distribution
        closed_trades = trades_df[trades_df['action'] == 'close']
        if not closed_trades.empty:
            profits = closed_trades[closed_trades['pnl'] > 0]['pnl']
            losses = closed_trades[closed_trades['pnl'] < 0]['pnl']
            
            axes[2].hist(profits, bins=20, alpha=0.6, color='green', label='Profits')
            axes[2].hist(losses, bins=20, alpha=0.6, color='red', label='Losses')
            axes[2].axvline(x=0, color='black', linestyle='--')
            axes[2].set_title('PnL Distribution')
            axes[2].set_xlabel('PnL (USDT)')
            axes[2].set_ylabel('Frequency')
            axes[2].legend()
            axes[2].grid(True)
        
        plt.tight_layout()
        filename = f'backtest_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(filename)
        print(f"\nResults saved to: {filename}")
        
        plt.show()
    
    def optimize_parameters(self):
        """Optymalizacja parametrów strategii"""
        print("Starting parameter optimization...")
        
        # Parametry do optymalizacji
        rsi_oversold_range = range(20, 35, 5)
        rsi_overbought_range = range(65, 80, 5)
        stop_loss_range = [1.0, 1.5, 2.0, 2.5, 3.0]
        take_profit_range = [1.5, 2.0, 2.5, 3.0, 4.0]
        
        results = []
        
        # Zachowaj oryginalne wartości
        original_rsi_oversold = Config.RSI_OVERSOLD
        original_rsi_overbought = Config.RSI_OVERBOUGHT
        original_stop_loss = Config.STOP_LOSS_PERCENT
        original_take_profit = Config.TAKE_PROFIT_PERCENT
        
        total_combinations = (len(rsi_oversold_range) * len(rsi_overbought_range) * 
                            len(stop_loss_range) * len(take_profit_range))
        
        current = 0
        
        for rsi_oversold in rsi_oversold_range:
            for rsi_overbought in rsi_overbought_range:
                for stop_loss in stop_loss_range:
                    for take_profit in take_profit_range:
                        current += 1
                        print(f"\rTesting combination {current}/{total_combinations}", end="")
                        
                        # Ustaw parametry
                        Config.RSI_OVERSOLD = rsi_oversold
                        Config.RSI_OVERBOUGHT = rsi_overbought
                        Config.STOP_LOSS_PERCENT = stop_loss
                        Config.TAKE_PROFIT_PERCENT = take_profit
                        
                        # Uruchom backtest
                        self.__init__()  # Reset
                        result = self.run_backtest(days=30, timeframe='5m')
                        
                        if result and result['metrics']:
                            results.append({
                                'rsi_oversold': rsi_oversold,
                                'rsi_overbought': rsi_overbought,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'total_return': result['metrics']['total_return'],
                                'win_rate': result['metrics']['win_rate'],
                                'profit_factor': result['metrics']['profit_factor'],
                                'max_drawdown_pct': result['metrics']['max_drawdown_pct']
                            })
        
        # Przywróć oryginalne wartości
        Config.RSI_OVERSOLD = original_rsi_oversold
        Config.RSI_OVERBOUGHT = original_rsi_overbought
        Config.STOP_LOSS_PERCENT = original_stop_loss
        Config.TAKE_PROFIT_PERCENT = original_take_profit
        
        # Znajdź najlepsze parametry
        if results:
            results_df = pd.DataFrame(results)
            best_return = results_df.loc[results_df['total_return'].idxmax()]
            best_profit_factor = results_df.loc[results_df['profit_factor'].idxmax()]
            best_win_rate = results_df.loc[results_df['win_rate'].idxmax()]
            
            print("\n\n" + "="*50)
            print("        OPTIMIZATION RESULTS")
            print("="*50)
            print("\nBest Return Parameters:")
            print(f"RSI Oversold:    {best_return['rsi_oversold']}")
            print(f"RSI Overbought:  {best_return['rsi_overbought']}")
            print(f"Stop Loss:       {best_return['stop_loss']}%")
            print(f"Take Profit:     {best_return['take_profit']}%")
            print(f"Total Return:    {best_return['total_return']:.2f}%")
            
            print("\nBest Profit Factor Parameters:")
            print(f"RSI Oversold:    {best_profit_factor['rsi_oversold']}")
            print(f"RSI Overbought:  {best_profit_factor['rsi_overbought']}")
            print(f"Stop Loss:       {best_profit_factor['stop_loss']}%")
            print(f"Take Profit:     {best_profit_factor['take_profit']}%")
            print(f"Profit Factor:   {best_profit_factor['profit_factor']:.2f}")
            
            # Zapisz wyniki
            results_df.to_csv(f'optimization_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            
        return results

if __name__ == "__main__":
    print("=== Bitget Futures Backtest Engine ===")
    print("1. Run backtest (30 days)")
    print("2. Optimize parameters")
    print("3. Custom backtest")
    
    choice = input("\nSelect option (1-3): ")
    
    backtest = BacktestEngine()
    
    if choice == '1':
        backtest.run_backtest(days=30, timeframe='5m')
    elif choice == '2':
        backtest.optimize_parameters()
    elif choice == '3':
        days = int(input("Enter number of days: "))
        timeframe = input("Enter timeframe (1m/5m/15m/1h): ")
        backtest.run_backtest(days=days, timeframe=timeframe)
    else:
        print("Invalid choice")