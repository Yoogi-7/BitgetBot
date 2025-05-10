# test_telegram.py
import os
from dotenv import load_dotenv
load_dotenv()

# Sprawdź czy zmienne są wczytane
print(f"Token: {os.getenv('TELEGRAM_BOT_TOKEN')[:10]}...")
print(f"Chat ID: {os.getenv('TELEGRAM_CHAT_ID')}")

from src.telegram_notifier import TelegramNotifier

notifier = TelegramNotifier()
notifier.send_message("🚀 Cześć! Bot działa poprawnie!")
notifier.notify_trade_opened("long", 103500, 50, "Test signal - RSI oversold")

print("Sprawdź Telegram - powinieneś dostać wiadomości!")