# src/logger.py
import csv
import json
import os
from datetime import datetime
from typing import Dict, List


class TradeLogger:
    """Simplified trade logging."""
    
    def __init__(self, filename: str = 'trading_history.csv'):
        self.filename = filename
        self.initialize_csv()
    
    def initialize_csv(self):
        """Initialize CSV file with headers."""
        if not os.path.exists(self.filename):
            headers = [
                'timestamp', 'action', 'side', 'price', 'size', 'pnl', 
                'reason', 'rsi', 'trend', 'balance_after'
            ]
            with open(self.filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(headers)
    
    def log_trade(self, trade_data: Dict):
        """Log trade to CSV."""
        with open(self.filename, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                trade_data.get('timestamp', datetime.now().isoformat()),
                trade_data.get('action', ''),
                trade_data.get('side', ''),
                trade_data.get('price', 0),
                trade_data.get('size', 0),
                trade_data.get('pnl', 0),
                trade_data.get('reason', ''),
                trade_data.get('rsi', 0),
                trade_data.get('trend', ''),
                trade_data.get('balance_after', 0)
            ])
    
    def generate_daily_summary(self, trading_data: Dict) -> Dict:
        """Generate daily trading summary."""
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_trades': trading_data.get('trades_today', 0),
            'daily_pnl': trading_data.get('daily_pnl', 0),
            'final_balance': trading_data.get('final_balance', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        # Save summary
        filename = f"summary_{summary['date']}.json"
        with open(filename, 'w') as file:
            json.dump(summary, file, indent=4)
        
        return summary