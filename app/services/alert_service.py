from app.core.telegram import TelegramBot

class AlertService:
    def __init__(self):
        self.telegram = TelegramBot()

    def send(self, message: str):
        print("[ALERT]", message)

        # 실제 연결 시 사용
        self.telegram.send_message(message)