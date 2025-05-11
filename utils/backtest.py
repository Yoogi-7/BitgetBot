# utils/backtest.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from src.exchange import ExchangeConnector
from src.strategy import TradingStrategy
from src.market_analyzer import MarketAnalyzer
from config.settings import Config


class BacktestEngine:
    """Simplified backtesting engine."""
    
    def __init__(self):
        self.exchange = ExchangeConnector()
        self.strategy = TradingStrategy()
        self.market_analyzer = MarketAnalyzer()
        
        # Backtest state
        self.initial_balance = 1000.0
        self.balance = self.initial_balance
        self.trades = []
        self.positions = []
    
    def run_backtest(self, days: int = 30, timeframe: str = '5m') -> Dict:
        """Run backtest for specified period."""
        print(f"Starting backtest for {days} days...")
        
        # Calculate required candles
        candles_needed = self._calculate_candles(days, timeframe)
        
        # Fetch historical data
        df = self.exchange.get_ohlcv(
            timeframe=timeframe,
            limit=candles_needed
        )
        
        if df is None or df.empty:
            print("Error: No data received")
            return {}
        
        print(f"Loaded {len(df)} candles")
        
        # Run simulation
        for i in range(100, len(df)):
            current_data = df.iloc[:i+1].copy()
            current_price = current_data.iloc[-1]['close']
            current_time = current_data.iloc[-1]['timestamp']
            
            # Prepare market data
            market_data = {
                'ohlcv': current_data,
                'ticker': {'last': current_price},
                'order_book': None,  # Simplified - no order book in backtest
                'recent_trades': None
            }
            
            # Get analysis and signal
            analysis = self.market_analyzer.analyze(market_data)
            signal = self.strategy.generate_signal(market_data, analysis, self.positions)
            
            # Execute trading logic
            self._execute_backtest_logic(signal, current_price, current_time)
            
            # Update positions
            self._update_positions(current_price)
        
        # Close any remaining positions
        self._close_all_positions(df.iloc[-1]['close'], df.iloc[-1]['timestamp'])
        
        # Generate report
        return self._generate_backtest_report()
    
    def _calculate_candles(self, days: int, timeframe: str) -> int:
        """Calculate number of candles needed."""
        minutes_per_candle = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        
        if timeframe not in minutes_per_candle:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        candles_per_day = 1440 / minutes_per_candle[timeframe]
        return min(int(candles_per_day * days), 1000)  # API limit
    
    def _execute_backtest_logic(self, signal: Dict, current_price: float, 
                               current_time: pd.Timestamp):
        """Execute trading logic in backtest."""
        if signal['action'] == 'OPEN' and signal['confidence'] >= 0.7:
            self._open_backtest_position(signal, current_price, current_time)
        elif signal['action'] == 'CLOSE':
            self._close_backtest_position(signal, current_price, current_time)
    
    def _open_backtest_position(self, signal: Dict, price: float, 
                               timestamp: pd.Timestamp):
        """Open position in backtest."""
        # Check if we can open position
        if len(self.positions) >= Config.MAX_OPEN_POSITIONS:
            return
        
        position_size_usd = min(Config.TRADE_AMOUNT_USDT, self.balance * 0.95)
        
        if position_size_usd < 10:  # Minimum trade size
            return
        
        position = {
            'side': signal['side'],
            'entry_price': price,
            'size': position_size_usd / price,
            'size_usd': position_size_usd,
            'opened_at': timestamp,
            'unrealized_pnl': 0
        }
        
        self.positions.append(position)
        self.balance -= position_size_usd
        
        self.trades.append({
            'timestamp': timestamp,
            'action': 'open',
            'side': signal['side'],
            'price': price,
            'size': position_size_usd,
            'reason': signal['reason'],
            'balance_after': self.balance
        })
    
    def _close_backtest_position(self, signal: Dict, price: float, 
                                timestamp: pd.Timestamp):
        """Close position in backtest."""
        for position in self.positions[:]:
            if position['side'] == signal['side']:
                pnl = self._calculate_pnl(position, price)
                self.balance += position['size_usd'] + pnl
                
                self.trades.append({
                    'timestamp': timestamp,
                    'action': 'close',
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'size': position['size_usd'],
                    'pnl': pnl,
                    'reason': signal['reason'],
                    'balance_after': self.balance
                })
                
                self.positions.remove(position)
                break
    
    def _update_positions(self, current_price: float):
        """Update position P&L and check stop loss/take profit."""
        for position in self.positions[:]:
            # Update unrealized PnL
            position['unrealized_pnl'] = self._calculate_pnl(position, current_price)
            
            # Check stop loss and take profit
            should_close = False
            reason = ""
            
            if position['side'] == 'long':
                if current_price <= position['entry_price'] * (1 - Config.STOP_LOSS_PERCENT/100):
                    should_close = True
                    reason = "Stop loss"
                elif current_price >= position['entry_price'] * (1 + Config.TAKE_PROFIT_PERCENT/100):
                    should_close = True
                    reason = "Take profit"
            else:  # short
                if current_price >= position['entry_price'] * (1 + Config.STOP_LOSS_PERCENT/100):
                    should_close = True
                    reason = "Stop loss"
                elif current_price <= position['entry_price'] * (1 - Config.TAKE_PROFIT_PERCENT/100):
                    should_close = True
                    reason = "Take profit"
            
            if should_close:
                dummy_signal = {'side': position['side'], 'reason': reason}
                self._close_backtest_position(dummy_signal, current_price, pd.Timestamp.now())
    
    def _calculate_pnl(self, position: Dict, current_price: float) -> float:
        """Calculate position PnL."""
        if position['side'] == 'long':
            return (current_price - position['entry_price']) * position['size']
        else:
            return (position['entry_price'] - current_price) * position['size']
    
    def _close_all_positions(self, final_price: float, timestamp: pd.Timestamp):
        """Close all remaining positions at end of backtest."""
        for position in self.positions[:]:
            dummy_signal = {'side': position['side'], 'reason': 'Backtest end'}
            self._close_backtest_position(dummy_signal, final_price, timestamp)
    
    def _generate_backtest_report(self) -> Dict:
        """Generate backtest report."""
        if not self.trades:
            print("No trades executed during backtest")
            return {}
        
        trades_df = pd.DataFrame(self.trades)
        closed_trades = trades_df[trades_df['action'] == 'close']
        
        if closed_trades.empty:
            print("No closed trades in backtest")
            return {}
        
        # Calculate metrics
        total_trades = len(closed_trades)
        winning_trades = closed_trades[closed_trades['pnl'] > 0]
        
        win_rate = len(winning_trades) / total_trades * 100
        total_pnl = closed_trades['pnl'].sum()
        final_balance = self.balance
        total_return = (final_balance - self.initial_balance) / self.initial_balance * 100
        
        # Print report
        print("\n" + "="*50)
        print("           BACKTEST RESULTS")
        print("="*50)
        print(f"Initial Balance:    ${self.initial_balance:.2f}")
        print(f"Final Balance:      ${final_balance:.2f}")
        print(f"Total Return:       {total_return:.2f}%")
        print(f"Total PnL:          ${total_pnl:.2f}")
        print(f"Total Trades:       {total_trades}")
        print(f"Win Rate:           {win_rate:.1f}%")
        print("="*50)
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_return': total_return,
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'trades': trades_df
        }


if __name__ == "__main__":
    print("=== Backtest Engine ===")
    print("1. Quick backtest (7 days)")
    print("2. Standard backtest (30 days)")
    print("3. Custom backtest")
    
    choice = input("\nSelect option (1-3): ")
    
    backtest = BacktestEngine()
    
    if choice == '1':
        backtest.run_backtest(days=7, timeframe='5m')
    elif choice == '2':
        backtest.run_backtest(days=30, timeframe='5m')
    elif choice == '3':
        days = int(input("Enter number of days: "))
        timeframe = input("Enter timeframe (1m/5m/15m/1h): ")
        backtest.run_backtest(days=days, timeframe=timeframe)
    else:
        print("Invalid choice")