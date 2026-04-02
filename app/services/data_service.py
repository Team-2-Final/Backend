from app.services.ai_service import AIService
from app.services.alert_service import AlertService

class DataService:
    def __init__(self):
        self.ai_service = AIService()
        self.alert_service = AlertService()

    def process(self, data: dict):
        # 1. AI 분석
        ai_result = self.ai_service.analyze(data)

        # 2. 알림 처리
        if ai_result["decision"] == "water":
            message = f"[ALERT] 물 필요 | confidence={ai_result['confidence']}"
            self.alert_service.send(message)

        # 3. 결과 반환
        return {
            "input": data,
            "ai_result": ai_result
        }