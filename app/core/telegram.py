import requests
from app.core.config import settings


class TelegramBot:
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id

    def send_message(self, message: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": message
        }

        response = requests.post(url, json=payload)

        if response.status_code != 200:
            print("❌ Telegram send failed:", response.text)