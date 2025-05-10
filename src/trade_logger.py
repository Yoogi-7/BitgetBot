# src/trade_logger.py
import csv
import os
from datetime import datetime
import json

class TradeLogger:
    def __init__(self, filename='trading_history.csv'):
        self.filename = filename
        self.initialize_csv()
    
    def initialize_csv(self):
        """Tworzy plik CSV z nagłówkami jeśli nie istnieje"""
        if not os.path.exists(self.filename):
            headers = ['timestamp', 'action', 'side', 'price', 'size_usd', 'pnl', 'reason', 'rsi', 'trend', 'balance_after']
            with open(self.filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(headers)
    
    def log_trade(self, trade_data):
        """Zapisuje transakcję do CSV"""
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
    
    def save_daily_summary(self, summary_data):
        """Zapisuje dzienne podsumowanie"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f'summary_{date_str}.json'
        
        with open(filename, 'w') as file:
            json.dump(summary_data, file, indent=4)