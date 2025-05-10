# src/telegram_notifier.py
import requests
import logging
from config.settings import Config

class TelegramNotifier:
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.logger = logging.getLogger(__name__)
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            self.logger.warning("Telegram notifications disabled - missing bot token or chat ID")
    
    def send_message(self, message, parse_mode='HTML'):
        """Wysyła wiadomość na Telegram"""
        if not self.enabled:
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, data=payload)
            
            if response.status_code != 200:
                self.logger.error(f"Failed to send Telegram message: {response.text}")
            
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")
    
    def notify_trade_opened(self, side, price, size_usd, reason):
        """Powiadomienie o otwarciu pozycji"""
        emoji = "🟢" if side == "long" else "🔴"
        message = f"""
{emoji} <b>New Position Opened</b>
Side: {side.upper()}
Price: ${price:.2f}
Size: ${size_usd:.2f}
Reason: {reason}
        """
        self.send_message(message)
    
    def notify_trade_closed(self, side, entry_price, exit_price, pnl, reason):
        """Powiadomienie o zamknięciu pozycji"""
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
    
    def notify_daily_summary(self, summary):
        """Powiadomienie z dziennym podsumowaniem"""
        win_rate = summary.get('win_rate', 0)
        total_pnl = summary.get('daily_pnl', 0)
        trades = summary.get('total_trades', 0)
        
        emoji = "📈" if total_pnl > 0 else "📉"
        
        message = f"""
{emoji} <b>Daily Summary</b>
Date: {summary.get('date', 'N/A')}
Total Trades: {trades}
Daily PnL: ${total_pnl:.2f}
Win Rate: {win_rate:.1f}%
        """
        self.send_message(message)
    
    def notify_error(self, error_message):
        """Powiadomienie o błędzie"""
        message = f"""
⚠️ <b>Bot Error</b>
{error_message}
        """
        self.send_message(message)
    
    def notify_bot_start(self):
        """Powiadomienie o starcie bota"""
        message = f"""
🚀 <b>Trading Bot Started</b>
Mode: {'PAPER' if Config.PAPER_TRADING else 'LIVE'}
Symbol: {Config.TRADING_SYMBOL}
Leverage: {Config.LEVERAGE}x
        """
        self.send_message(message)
    
    def notify_bot_stop(self):
        """Powiadomienie o zatrzymaniu bota"""
        message = "🛑 <b>Trading Bot Stopped</b>"
        self.send_message(message)