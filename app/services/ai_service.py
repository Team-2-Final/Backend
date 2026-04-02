class AIService:
    def analyze(self, data: dict):
        # mock 로직 (독립 테스트용)

        if data["soil_moisture"] < 30:
            return {
                "decision": "water",
                "confidence": 0.9
            }
        else:
            return {
                "decision": "normal",
                "confidence": 0.8
            }