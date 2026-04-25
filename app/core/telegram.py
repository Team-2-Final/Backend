import requests
from app.core.config import settings


class TelegramBot:
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id

    def send(self, message: str = None, image_path: str = None):
        # 1️⃣ 이미지 있는 경우 → sendPhoto
        if image_path:
            url = f"https://api.telegram.org/bot{self.token}/sendPhoto"

            with open(image_path, "rb") as photo:
                files = {
                    "photo": photo
                }
                data = {
                    "chat_id": self.chat_id,
                    "caption": message or ""
                }

                response = requests.post(url, files=files, data=data)

        # 2️⃣ 텍스트만 → sendMessage
        else:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"

            payload = {
                "chat_id": self.chat_id,
                "text": message
            }

            response = requests.post(url, json=payload)

        if response.status_code != 200:
            print("❌ Telegram send failed:", response.text)