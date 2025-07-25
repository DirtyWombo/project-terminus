import os
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AlertManager:
    def __init__(self):
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logging.warning("Telegram API credentials not fully set. Telegram alerts will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logging.info("Telegram Alert Manager initialized.")

    def send_telegram_message(self, message):
        if not self.enabled:
            return
        
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            logging.info(f"Telegram message sent: {message}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending Telegram message: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred while sending Telegram message: {e}")

# Initialize globally for the trader_app
alert_manager = AlertManager()
