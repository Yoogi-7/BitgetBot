# utils/backtest.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from src.exchange import ExchangeConnector
from src.strategy import TradingStrategy
from src.market_analyzer import MarketAnalyzer
from src.risk_manager import RiskManager
from config.settings import Config


class BacktestEngine:
    """Enhanced backtesting engine with slippage and flash crash simulation."""
    
    def __init__(self, slippage_pct: float = 0.05, fees_pct: float = 0.1):
        self.exchange = ExchangeConnector()
        self.strategy = TradingStrategy()
        self.market_analyzer = MarketAnalyzer()
        self.risk_manager = RiskManager()
        
        # Backtest parameters
        self.slippage_pct = slippage_pct / 100  # Convert to decimal
        self.fees_pct = fees_pct / 100  # Convert to decimal
        
        # Backtest state
        self.initial_balance = 1000.0
        self.balance = self.initial_balance
        self.trades = []
        self.positions = []
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0
        self.peak_balance = self.initial_balance
        self.max_drawdown = 0
    
    def run_backtest(self, days: int = 30, timeframe: str = '1m', 
                     flash_crash_dates: List[str] = None) -> Dict:
        """Run backtest with optional flash crash simulation."""
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
        
        # Add flash crash simulation if dates provided
        if flash_crash_dates:
            df = self._add_flash_crash_simulation(df, flash_crash_dates)
        
        # Run simulation
        for i in range(100, len(df)):
            current_data = df.iloc[:i+1].copy()
            current_price = current_data.iloc[-1]['close']
            current_time = current_data.iloc[-1]['timestamp']
            current_spread = self._calculate_spread(current_data)
            
            # Prepare market data
            market_data = {
                'ohlcv': current_data,
                'ticker': {
                    'last': current_price,
                    'spread': current_spread
                },
                'order_book': self._simulate_order_book(current_price, current_spread),
                'recent_trades': self._simulate_recent_trades(current_price)
            }
            
            # Get analysis and signal
            analysis = self.market_analyzer.analyze(market_data)
            signal = self.strategy.generate_signal(market_data, analysis, self.positions)
            
            # Check risk management
            if signal['action'] == 'OPEN':
                if not self.risk_manager.is_strategy_allowed(signal.get('reason', '')):
                    continue
            
            # Execute trading logic
            self._execute_backtest_logic(signal, current_price, current_time, current_spread)
            
            # Update positions
            self._update_positions(current_price)
            
            # Update performance metrics
            self._update_metrics()
        
        # Close any remaining positions
        self._close_all_positions(df.iloc[-1]['close'], df.iloc[-1]['timestamp'])
        
        # Generate report
        return self._generate_backtest_report()
    
    def _calculate_spread(self, df: pd.DataFrame) -> float:
        """Calculate realistic spread based on volatility."""
        # Base spread: 0.05% + volatility-based component
        volatility = df['close'].pct_change().std()
        return 0.0005 + volatility * 0.1
    
    def _simulate_order_book(self, price: float, spread: float) -> Dict:
        """Simulate order book for backtest."""
        bid_price = price * (1 - spread/2)
        ask_price = price * (1 + spread/2)
        
        # Simulate L2 data
        bids = [[bid_price - i*0.0001*price, np.random.uniform(0.1, 1.0)] for i in range(5)]
        asks = [[ask_price + i*0.0001*price, np.random.uniform(0.1, 1.0)] for i in range(5)]
        
        return {
            'bids': bids,
            'asks': asks,
            'full_bids': bids,
            'full_asks': asks,
            'timestamp': pd.Timestamp.now()
        }
    
    def _simulate_recent_trades(self, price: float) -> List[Dict]:
        """Simulate recent trades for backtest."""
        trades = []
        for i in range(20):
            trades.append({
                'price': price + np.random.uniform(-0.001, 0.001) * price,
                'amount': np.random.uniform(0.01, 0.5),
                'side': np.random.choice(['buy', 'sell']),
                'timestamp': pd.Timestamp.now() - pd.Timedelta(seconds=i)
            })
        return trades
    
    def _add_flash_crash_simulation(self, df: pd.DataFrame, flash_crash_dates: List[str]) -> pd.DataFrame:
        """Add flash crash events to historical data."""
        for crash_date in flash_crash_dates:
            # Find the date in the dataframe
            mask = df['timestamp'].dt.date == pd.to_datetime(crash_date).date()
            if mask.any():
                # Simulate flash crash: 10-20% drop
                crash_magnitude = np.random.uniform(0.10, 0.20)
                df.loc[mask, 'low'] *= (1 - crash_magnitude)
                df.loc[mask, 'close'] *= (1 - crash_magnitude * 0.8)  # Partial recovery
                
                # Increase volume during crash
                df.loc[mask, 'volume'] *= 5
                
                print(f"Added flash crash simulation for {crash_date} ({crash_magnitude*100:.1f}% drop)")
        
        return df
    
    def _execute_backtest_logic(self, signal: Dict, current_price: float, 
                               current_time: pd.Timestamp, spread: float):
        """Execute trading logic in backtest with slippage."""
        if signal['action'] == 'OPEN' and signal['confidence'] >= 0.7:
            # Apply slippage to entry
            if signal['side'] == 'long':
                entry_price = current_price * (1 + self.slippage_pct + spread)
            else:
                entry_price = current_price * (1 - self.slippage_pct - spread)
            
            self._open_backtest_position(signal, entry_price, current_time)
        
        elif signal['action'] == 'CLOSE':
            # Apply slippage to exit
            if signal['side'] == 'long':
                exit_price = current_price * (1 - self.slippage_pct - spread)
            else:
                exit_price = current_price * (1 + self.slippage_pct + spread)
            
            self._close_backtest_position(signal, exit_price, current_time)
    
    def _open_backtest_position(self, signal: Dict, price: float, 
                               timestamp: pd.Timestamp):
        """Open position in backtest with fees."""
        if len(self.positions) >= Config.MAX_OPEN_POSITIONS:
            return
        
        # Calculate position size with risk management
        atr = signal.get('atr', 0.02 * price)
        position_size_usd = self.risk_manager.calculate_position_size(
            self.balance, price, atr
        )
        
        # Apply fees
        fees = position_size_usd * self.fees_pct
        position_size_usd -= fees
        
        if position_size_usd < 10:  # Minimum trade size
            return
        
        position = {
            'side': signal['side'],
            'entry_price': price,
            'size': position_size_usd / price,
            'size_usd': position_size_usd,
            'opened_at': timestamp,
            'unrealized_pnl': 0,
            'fees_paid': fees
        }
        
        self.positions.append(position)
        self.balance -= (position_size_usd + fees)
        
        self.trades.append({
            'timestamp': timestamp,
            'action': 'open',
            'side': signal['side'],
            'price': price,
            'size': position_size_usd,
            'reason': signal['reason'],
            'balance_after': self.balance,
            'fees': fees
        })
        
        self.risk_manager.record_trade({
            'action': 'open',
            'side': signal['side'],
            'price': price,
            'size': position_size_usd,
            'reason': signal['reason']
        })
    
    def _close_backtest_position(self, signal: Dict, price: float, 
                                timestamp: pd.Timestamp):
        """Close position in backtest with fees."""
        for position in self.positions[:]:
            if position['side'] == signal['side']:
                # Calculate PnL
                gross_pnl = self._calculate_pnl(position, price)
                
                # Apply fees
                exit_value = position['size'] * price
                fees = exit_value * self.fees_pct
                net_pnl = gross_pnl - fees - position['fees_paid']
                
                self.balance += exit_value - fees
                
                # Update metrics
                self.total_trades += 1
                if net_pnl > 0:
                    self.winning_trades += 1
                self.total_pnl += net_pnl
                
                self.trades.append({
                    'timestamp': timestamp,
                    'action': 'close',
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'size': position['size_usd'],
                    'gross_pnl': gross_pnl,
                    'net_pnl': net_pnl,
                    'fees': fees + position['fees_paid'],
                    'reason': signal['reason'],
                    'balance_after': self.balance
                })
                
                self.risk_manager.record_trade({
                    'action': 'close',
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'size': position['size_usd'],
                    'pnl': net_pnl,
                    'reason': signal['reason']
                })
                
                self.positions.remove(position)
                break
    
    def _update_metrics(self):
        """Update performance metrics."""
        current_balance = self.balance + sum(p['unrealized_pnl'] for p in self.positions)
        
        # Peak and drawdown
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        drawdown = (self.peak_balance - current_balance) / self.peak_balance
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    def _generate_backtest_report(self) -> Dict:
        """Generate comprehensive backtest report."""
        if not self.trades:
            print("No trades executed during backtest")
            return {}
        
        trades_df = pd.DataFrame(self.trades)
        closed_trades = trades_df[trades_df['action'] == 'close']
        
        if closed_trades.empty:
            print("No closed trades in backtest")
            return {}
        
        # Calculate metrics
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        # Profit factor
        winning_pnl = closed_trades[closed_trades['net_pnl'] > 0]['net_pnl'].sum()
        losing_pnl = abs(closed_trades[closed_trades['net_pnl'] < 0]['net_pnl'].sum())
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
        
        # Total return
        total_return = ((self.balance - self.initial_balance) / self.initial_balance) * 100
        
        # Print report
        print("\n" + "="*50)
        print("           BACKTEST RESULTS")
        print("="*50)
        print(f"Initial Balance:    ${self.initial_balance:.2f}")
        print(f"Final Balance:      ${self.balance:.2f}")
        print(f"Total Return:       {total_return:.2f}%")
        print(f"Total PnL:          ${self.total_pnl:.2f}")
        print(f"Total Trades:       {self.total_trades}")
        print(f"Win Rate:           {win_rate:.1f}%")
        print(f"Profit Factor:      {profit_factor:.2f}")
        print(f"Max Drawdown:       {self.max_drawdown*100:.1f}%")
        print("="*50)
        
        # Target metrics check
        if win_rate > 60 and profit_factor > 1.5:
            print("✅ TARGET ACHIEVED: Win rate > 60%, Profit factor > 1.5")
        else:
            print("❌ TARGET NOT MET: Win rate > 60%, Profit factor > 1.5")
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_return': total_return,
            'total_pnl': self.total_pnl,
            'total_trades': self.total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': self.max_drawdown,
            'trades': trades_df
        }


if __name__ == "__main__":
    print("=== Enhanced Backtest Engine ===")
    print("1. Standard backtest (30 days)")
    print("2. Flash crash simulation (March 12, 2020)")
    print("3. FTX collapse simulation")
    print("4. Custom backtest")
    
    choice = input("\nSelect option (1-4): ")
    
    backtest = BacktestEngine(slippage_pct=0.05, fees_pct=0.1)
    
    if choice == '1':
        backtest.run_backtest(days=30, timeframe='1m')
    elif choice == '2':
        # COVID crash
        backtest.run_backtest(days=60, timeframe='1m', 
                            flash_crash_dates=['2020-03-12'])
    elif choice == '3':
        # FTX collapse
        backtest.run_backtest(days=30, timeframe='1m',
                            flash_crash_dates=['2022-11-08'])
    elif choice == '4':
        days = int(input("Enter number of days: "))
        timeframe = input("Enter timeframe (1m/5m/15m/1h): ")
        slippage = float(input("Enter slippage % (e.g., 0.05): "))
        fees = float(input("Enter fees % (e.g., 0.1): "))
        
        custom_backtest = BacktestEngine(slippage_pct=slippage, fees_pct=fees)
        custom_backtest.run_backtest(days=days, timeframe=timeframe)
    else:
        print("Invalid choice")