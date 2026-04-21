from datetime import datetime, timezone
import uuid
import os

from app.db.oracle import SessionLocal

from app.services.ai_service import AIService
from app.services.alert_service import AlertService
from app.services.mongo_service import MongoService
from app.services.dashboard_service import DashboardService
from app.websocket.manager import ws_manager

from app.models.oracle.growth_batch import GrowthBatch
from app.models.oracle.environment_data import EnvironmentData

from app.models.oracle.plant_growth import PlantGrowth
from app.models.oracle.ai_result import AIResult
from app.models.oracle.action_log import ActionLog
from app.models.oracle.image_data import ImageData


class DataService:
    def __init__(self):
        self.ai_service = AIService()
        self.alert_service = AlertService()
        self.mongo_service = MongoService()
        self.dashboard_service = DashboardService()

    # ai 판단 종류
    EVENT_TYPES = {"disease", "harvest", "flowering"}
    async def process(self, batch_id: int, image_file=None):

        db = SessionLocal()
        


        try:
            now = datetime.now()

            # =====================================
            # 1️⃣ 이미지 저장 (파일)
            # =====================================
            image_path = None

            if image_file:
                image_path = self._save_image(image_file, batch_id)

                db.add(ImageData(
                    batch_id=batch_id,
                    inference_id=None,
                    file_path=image_path,
                    captured_at=now
                ))

            # =====================================
            # 2️⃣ AI 분석 (이미지만 입력)
            # =====================================
            ai_output = self.ai_service.analyze(image_path)

            inference_id = ai_output.get("inference_id", str(uuid.uuid4()))
            
            event = ai_output["ai_result"]
            
            result_type = event.get("result_type")
            is_event = result_type in self.EVENT_TYPES

            # =====================================
            # 3️⃣ plant_growth (STREAM → Oracle)
            # =====================================
            pg = ai_output["plant_growth"]

            db.add(PlantGrowth(
                batch_id=batch_id,
                inference_id=inference_id,

                plant_height=pg["plant_height"],
                leaf_length=pg["leaf_length"],
                leaf_width=pg["leaf_width"],
                leaf_count=pg["leaf_count"],

                captured_at=ai_output.get("captured_at", now),
                inferred_at=ai_output.get("inferred_at", now)
            ))

            # =====================================
            # 4️⃣ ai_result (EVENT → Oracle)
            # =====================================
            if is_event:
                db.add(AIResult(
                    batch_id=batch_id,
                    inference_id=inference_id,
                    model_version=ai_output.get("model_version", "v1.0"),

                    result_type=event["result_type"],
                    result_value=event["result_value"],
                    confidence=event["confidence"],
                    severity=event["severity"],

                    captured_at=ai_output.get("captured_at", now),
                    inferred_at=ai_output.get("inferred_at", now)
                ))

            # =====================================
            # 5️⃣ MongoDB (AI 상세 결과 저장)
            # =====================================
            mongo_payload = {
                "inference_id": inference_id,
                "model_version": ai_output.get("model_version", "v1.0"),

                "image_path": image_path,

                "raw_output": ai_output,

                "detections": ai_output.get("detections", []),

                "extra_metrics": {
                    "source": "data_service"
                },

                "captured_at": ai_output.get("captured_at", now),
                "inferred_at": ai_output.get("inferred_at", now)
            }

            print("🔥 before mongo")

            if is_event:
                await self.mongo_service.save_ai_detail(mongo_payload)
            
            print("🔥 after mongo")
            # =====================================
            # 6️⃣ EVENT 기반 action 처리
            # =====================================
            if (
                is_event 
                and event["confidence"] > 0.8
                and event["severity"] >= 3
                ):
                 
                short_msg, detail_msg = self._build_messages(event)
                
                # 텔레그램용 메시지 전송
                self.alert_service.send(detail_msg)

                db.add(ActionLog(
                    batch_id=batch_id,
                    action_type=event["result_type"],
                    action_mode="auto",

                    trigger_value=None,
                    threshold=None,

                    status="triggered",
                    message=short_msg,

                ))

            # =====================================
            # 7️⃣ commit
            # =====================================
            db.commit()

            await ws_manager.broadcast(batch_id, {
                "type": "dashboard_update",
                "type": self.dashboard_service.get_dashboard(batch_id)
            })

            # =====================================
            # 8️⃣ response
            # =====================================
            return {
                "batch_id": batch_id,
                "inference_id": inference_id,
                "image_path": image_path,
                "ai_result": event,
                "plant_growth": pg
            }

        except Exception as e:
            db.rollback()
            raise e

        finally:
            db.close()

    # =====================================
    # 이미지 저장
    # =====================================
    def _save_image(self, file, batch_id):
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{batch_id}_{uuid.uuid4().hex}.jpg"
        path = os.path.join(upload_dir, filename)

        with open(path, "wb") as buffer:
            buffer.write(file.file.read())

        return path
    
    # ai 검사 결과에 따른 메시지 생성
    def _build_messages(self, event):
        if event["result_type"] == "disease":
            short = f"[disease] {event['result_value']}"
            detail = f"""
    🚨 병해 감지
    종류: {event['result_value']}
    심각도: {event['severity']}
    신뢰도: {event['confidence']}
    """
            return short, detail

        elif event["result_type"] == "harvest":
            short = f"[harvest] 수확 시기 도달"
            detail = f"""
    🌾 수확 시기 도달
    신뢰도: {event['confidence']}
    """
            return short, detail

        elif event["result_type"] == "flowering":
            short = f"[flowering] 개화 감지"
            detail = f"""
    🌸 개화 감지
    신뢰도: {event['confidence']}
    """
            return short, detail

        return None, None