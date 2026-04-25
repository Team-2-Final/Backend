from app.core.telegram import TelegramBot


class AlertService:
    def __init__(self):
        self.telegram = TelegramBot()

    def send(self, message: str = None, image_path: str = None):
        print("[ALERT]", message, image_path)

        self.telegram.send(message=message, image_path=image_path)