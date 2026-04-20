import uuid
from datetime import datetime


class AIService:

    def analyze(self, image_path: str):
        # mock AI 결과

        return {
            "inference_id": str(uuid.uuid4()),
            "model_version": "v1.0",

            "captured_at": datetime.now(),
            "inferred_at": datetime.now(),

            "plant_growth": {
                "plant_height": 12.3,
                "leaf_length": 5.2,
                "leaf_width": 2.1,
                "leaf_count": 6
            },

            "ai_result": {
                "result_type": "disease",
                "result_value": "blight",
                "confidence": 0.92,
                "severity": 3
            },

            "detections": []
        }