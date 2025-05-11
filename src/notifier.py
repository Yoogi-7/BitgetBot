# src/notifier.py
import requests
import logging
from typing import Dict
from config.settings import Config


class TelegramNotifier:
    """Simplified Telegram notifications."""
    
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.logger = logging.getLogger(__name__)
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            self.logger.info("Telegram notifications disabled")
    
    def send_message(self, message: str):
        """Send message to Telegram."""
        if not self.enabled:
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=payload)
            if response.status_code != 200:
                self.logger.error(f"Failed to send Telegram message: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")
    
    def notify_startup(self):
        """Notify bot startup."""
        mode = "PAPER" if Config.PAPER_TRADING else "LIVE"
        message = f"""
🚀 <b>Trading Bot Started</b>
Mode: {mode}
Symbol: {Config.TRADING_SYMBOL}
Leverage: {Config.LEVERAGE}x
        """
        self.send_message(message)
    
    def notify_trade_opened(self, side: str, price: float, size: float, reason: str):
        """Notify trade opened."""
        emoji = "🟢" if side == "long" else "🔴"
        message = f"""
{emoji} <b>Position Opened</b>
Side: {side.upper()}
Price: ${price:.2f}
Size: ${size:.2f}
Reason: {reason}
        """
        self.send_message(message)
    
    def notify_trade_closed(self, side: str, entry_price: float, 
                           exit_price: float, pnl: float, reason: str):
        """Notify trade closed."""
        emoji = "💰" if pnl > 0 else "💸"
        pnl_emoji = "✅" if pnl > 0 else "❌"
        
        message = f"""
{emoji} <b>Position Closed</b>
Side: {side.upper()}
Entry: ${entry_price:.2f}
Exit: ${exit_price:.2f}
PnL: ${pnl:.2f} {pnl_emoji}
Reason: {reason}
        """
        self.send_message(message)
    
    def notify_daily_summary(self, summary: Dict):
        """Notify daily summary."""
        pnl = summary.get('daily_pnl', 0)
        emoji = "📈" if pnl > 0 else "📉"
        
        message = f"""
{emoji} <b>Daily Summary</b>
Date: {summary.get('date', 'N/A')}
Total Trades: {summary.get('total_trades', 0)}
Daily PnL: ${pnl:.2f}
        """
        self.send_message(message)
    
    def notify_error(self, error_message: str):
        """Notify error."""
        message = f"""
⚠️ <b>Bot Error</b>
{error_message[:200]}
        """
        self.send_message(message)
    
    def notify_shutdown(self):
        """Notify bot shutdown."""
        self.send_message("🛑 <b>Trading Bot Stopped</b>")