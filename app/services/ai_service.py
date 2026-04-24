import uuid
from datetime import datetime
import requests
import os


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
    

    # 성장 분석 및 수확시기 분석
    def analyzeThree(self, image_path1, image_path2, image_path3=None):
        url = "http://127.0.0.1:8001/predict/growth"

        try:
            paths = [
                ("plant_image", image_path1),
                ("leaf_image", image_path2),
                ("fruit_image", image_path3),
            ]

            files = {}
            opened_files = []

            for key, path in paths:
                if path:
                    f = open(path, "rb")
                    opened_files.append(f)
                    files[key] = (os.path.basename(path), f, "image/jpeg")

            response = requests.post(url, files=files, timeout=30)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            return {"success": False, "error": str(e)}

        finally:
            for f in opened_files:
                f.close()


    # 개별 요청 세팅
    def infer_single(self, url: str, image_path: str):
        try:
            with open(image_path, "rb") as f:
                files = {
                    "file": (os.path.basename(image_path), f, "image/jpeg")
                }

                response = requests.post(url, files=files, timeout=30)
                response.raise_for_status()

                return response.json()

        except Exception as e:
            return {"success": False, "error": str(e)}
        

    # 잎 분석 요청    
    def analyze_leaf(self, image_path: str):
        return self.infer_single(
        "http://127.0.0.1:8002/infer/leaf",
        image_path
    )    

    # 열매 분석 요청
    def analyze_fruit(self, image_path: str):
        return self.infer_single(
        "http://127.0.0.1:8002/infer/fruit",
        image_path
    )