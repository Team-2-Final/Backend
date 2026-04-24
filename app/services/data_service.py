from datetime import datetime, timezone
import uuid
import os
from dateutil import parser

from app.db.oracle import SessionLocal

from app.services.ai_service import AIService
from app.services.alert_service import AlertService
from app.services.mongo_service import MongoService
from app.services.dashboard_service import DashboardService
from app.services.image_service import ImageService
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
        self.image_service = ImageService()

    # ai 판단 종류
    EVENT_TYPES = {"disease", "harvest", "flowering"}

    # 3개 이미지 받는 용도
    async def process3(self, batch_id: int, plant_image, leaf_image, fruit_image=None):
        print("process까지 옴")
        db = SessionLocal()     


        try:
            now = datetime.now()

            # =====================================
            # 1️⃣ 이미지 저장 (파일)
            # =====================================
            files = {
                "plant": plant_image,
                "leaf": leaf_image,
                "fruit": fruit_image
            }

            image_paths = {}

            for key, file in files.items():
                if file:
                    image_paths[key] = self.image_service.save_image(file, batch_id, key)


            for key, path in image_paths.items():
                db.add(ImageData(
                    batch_id=batch_id,
                    inference_id=None,
                    file_path=path,
                    captured_at=now,
                    recorded_at =now
                ))

            # =====================================
            # 2️⃣ AI 분석 (이미지만 입력)
            # =====================================
            ai_output = self.ai_service.analyzeThree(
                image_paths.get("plant"),
                image_paths.get("leaf"),
                image_paths.get("fruit")
            )            

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

                captured_at = self.normalize_datetime(ai_output.get("captured_at"), now),
                inferred_at = self.normalize_datetime(ai_output.get("inferred_at"), now),

                recorded_at =now

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

                    captured_at = self.normalize_datetime(ai_output.get("captured_at"), now),
                    inferred_at = self.normalize_datetime(ai_output.get("inferred_at"), now),
                    recorded_at= now
                ))

            # =====================================
            # 5️⃣ MongoDB (AI 상세 결과 저장)
            # =====================================
            mongo_payload = {
                "inference_id": inference_id,
                "model_version": ai_output.get("model_version", "v1.0"),

                "image_path": image_paths,

                "raw_output": ai_output,

                "detections": ai_output.get("detections", []),

                "extra_metrics": {
                    "source": "data_service"
                },

                "captured_at": self.normalize_datetime(ai_output.get("captured_at"), now),
                "inferred_at": self.normalize_datetime(ai_output.get("inferred_at"), now),

                "recorded_at": now,
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

                    recorded_at =now

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
                "image_path": image_paths,
                "ai_result": event,
                "plant_growth": pg
            }

        except Exception as e:
            db.rollback()
            raise e

        finally:
            db.close()


    async def infer_leaf(self, batch_id: int, file):
        now = datetime.now()

        # 1. 이미지 저장
        image_path = self.image_service.save_image(file, batch_id, "leaf")

        # 2. AI 분석
        ai_output = self.ai_service.analyze_leaf(image_path)

        inference_id = ai_output.get("inference_id", str(uuid.uuid4()))
        event = ai_output["ai_result"]

        is_event = event["result_type"] in self.EVENT_TYPES

        # 3. Oracle 저장
        db = SessionLocal()
        try:
            db.add(AIResult(
                batch_id=batch_id,
                inference_id=inference_id,
                model_version=ai_output.get("model_version", "v1.0"),

                result_type=event["result_type"],
                result_value=event["result_value"],
                confidence=event["confidence"],
                severity=event.get("severity", 0),

                captured_at=now,
                inferred_at=now,
                recorded_at=now
            ))

            # 4. EVENT 처리 (텔레그램 + ActionLog)
            if (
                is_event
                and event["confidence"] > 0.8
                and event.get("severity", 0) >= 3
            ):
                short_msg, detail_msg = self._build_messages(event)

                self.alert_service.send(detail_msg)

                db.add(ActionLog(
                    batch_id=batch_id,
                    action_type=event["result_type"],
                    action_mode="auto",
                    status="triggered",
                    message=short_msg,
                    recorded_at=now
                ))

            db.commit()

        except:
            db.rollback()
            raise
        finally:
            db.close()

        # 5. MongoDB 저장 (🔥 핵심 누락 부분)
        mongo_payload = {
            "inference_id": inference_id,
            "model_version": ai_output.get("model_version", "v1.0"),
            "image_path": image_path,
            "raw_output": ai_output,
            "captured_at": now,
            "inferred_at": now,
            "recorded_at": now,
        }

        if is_event:
            await self.mongo_service.save_ai_detail(mongo_payload)

        return {
            "batch_id": batch_id,
            "inference_id": inference_id,
            "result": event,
            "image_path": image_path
        }


    async def infer_fruit(self, batch_id: int, file):
        now = datetime.now()

        image_path = self.image_service.save_image(file, batch_id, "fruit")

        ai_output = self.ai_service.analyze_fruit(image_path)

        inference_id = ai_output.get("inference_id", str(uuid.uuid4()))
        event = ai_output["ai_result"]

        is_event = event["result_type"] in self.EVENT_TYPES

        db = SessionLocal()
        try:
            db.add(AIResult(
                batch_id=batch_id,
                inference_id=inference_id,
                model_version=ai_output.get("model_version", "v1.0"),

                result_type=event["result_type"],
                result_value=event["result_value"],
                confidence=event["confidence"],
                severity=event.get("severity", 0),

                captured_at=now,
                inferred_at=now,
                recorded_at=now
            ))

            # 🔥 EVENT 처리
            if (
                is_event
                and event["confidence"] > 0.8
                and event.get("severity", 0) >= 3
            ):
                short_msg, detail_msg = self._build_messages(event)

                self.alert_service.send(detail_msg)

                db.add(ActionLog(
                    batch_id=batch_id,
                    action_type=event["result_type"],
                    action_mode="auto",
                    status="triggered",
                    message=short_msg,
                    recorded_at=now
                ))

            db.commit()

        except:
            db.rollback()
            raise
        finally:
            db.close()

        # 🔥 MongoDB 저장
        mongo_payload = {
            "inference_id": inference_id,
            "model_version": ai_output.get("model_version", "v1.0"),
            "image_path": image_path,
            "raw_output": ai_output,
            "captured_at": now,
            "inferred_at": now,
            "recorded_at": now,
        }

        if is_event:
            await self.mongo_service.save_ai_detail(mongo_payload)

        return {
            "batch_id": batch_id,
            "inference_id": inference_id,
            "result": event,
            "image_path": image_path
        }




    
    # 문자를 날짜화
    def normalize_datetime(self, value, fallback):
        if value is None:
            return fallback

        if isinstance(value, str):
            dt = parser.isoparse(value)
            return dt.replace(tzinfo=None)

        return value


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