# run_bot.py
import subprocess
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_runner.log'),
        logging.StreamHandler()
    ]
)

def run_bot():
    """Uruchamia bota z automatycznym restartem"""
    while True:
        try:
            logging.info("Starting trading bot...")
            # Uruchom główny skrypt
            process = subprocess.Popen(['python', 'main.py'])
            process.wait()
            
            # Jeśli bot się zatrzymał, poczekaj i zrestartuj
            logging.warning("Bot stopped. Restarting in 30 seconds...")
            time.sleep(30)
            
        except KeyboardInterrupt:
            logging.info("Bot runner stopped by user")
            if process:
                process.terminate()
            break
        except Exception as e:
            logging.error(f"Error in bot runner: {e}")
            time.sleep(60)  # Poczekaj minutę przed ponowną próbą

if __name__ == "__main__":
    run_bot()