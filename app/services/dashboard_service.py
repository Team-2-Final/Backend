from app.db.oracle import SessionLocal
from app.models.oracle.environment_data import EnvironmentData
from app.models.oracle.plant_growth import PlantGrowth
from app.models.oracle.ai_result import AIResult
from app.models.oracle.action_log import ActionLog
from datetime import datetime, timedelta


class DashboardService:
    def _clamp(self, value: float, min_value: float = 0, max_value: float = 100):
        return max(min_value, min(max_value, value))

    def _score_range(self, value, good_min, good_max, weight):
        if value is None:
            return weight * 0.5

        if good_min <= value <= good_max:
            return weight

        if value < good_min:
            diff = good_min - value
        else:
            diff = value - good_max

        penalty = diff * (weight / 10)
        return self._clamp(weight - penalty, 0, weight)

    def _fmt_time(self, dt):
        if not dt:
            return None
        return dt.strftime("%H:%M")

    def _fmt_datetime(self, dt):
        if not dt:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _get_latest_environment_row(self, db, batch_id: int):
        return (
            db.query(EnvironmentData)
            .filter(EnvironmentData.batch_id == batch_id)
            .order_by(EnvironmentData.id.desc())
            .first()
        )

    def _get_previous_environment_row(self, db, batch_id: int):
        rows = (
            db.query(EnvironmentData)
            .filter(EnvironmentData.batch_id == batch_id)
            .order_by(EnvironmentData.id.desc())
            .limit(2)
            .all()
        )
        return rows[1] if len(rows) >= 2 else None

    def _get_latest_growth_row(self, db, batch_id: int):
        return (
         db.query(PlantGrowth)
        .filter(PlantGrowth.batch_id == batch_id)
        .order_by(PlantGrowth.recorded_at.desc(), PlantGrowth.id.desc())
        .first()
    )

    def _get_latest_ai_row(self, db, batch_id: int):
        return (
            db.query(AIResult)
            .filter(AIResult.batch_id == batch_id)
            .order_by(AIResult.id.desc())
            .first()
        )

    def _get_recent_issue_count(self, db, batch_id: int, limit: int = 5):
        rows = (
            db.query(ActionLog)
            .filter(ActionLog.batch_id == batch_id)
            .order_by(ActionLog.id.desc())
            .limit(limit)
            .all()
        )

        count = 0
        for row in rows:
            if row.status in ["fail", "triggered"]:
                count += 1
        return count

    def get_latest_sensors(self, batch_id: int):
        db = SessionLocal()
        try:
            latest = self._get_latest_environment_row(db, batch_id)
            prev = self._get_previous_environment_row(db, batch_id)

            if not latest:
                return {
                    "temperature": {"value": None, "delta": None, "unit": "°C"},
                    "humidity": {"value": None, "delta": None, "unit": "%"},
                    "co2": {"value": None, "delta": None, "unit": "ppm"},
                    "radiation": {"value": None, "delta": None, "unit": "W/m²"},
                    "soil_ec": {"value": None, "delta": None, "unit": "dS/m"},
                    "soil_ph": {"value": None, "delta": None, "unit": "pH"},
                    "soil_moisture": {"value": None, "delta": None, "unit": "%"},
                    "recorded_at": None,
                }

            def delta(curr, old):
                if curr is None or old is None:
                    return None
                return round(curr - old, 1)

            return {
                "temperature": {
                    "value": latest.temperature,
                    "delta": delta(latest.temperature, prev.temperature if prev else None),
                    "unit": "°C",
                },
                "humidity": {
                    "value": latest.humidity,
                    "delta": delta(latest.humidity, prev.humidity if prev else None),
                    "unit": "%",
                },
                "co2": {
                    "value": latest.co2,
                    "delta": delta(latest.co2, prev.co2 if prev else None),
                    "unit": "ppm",
                },
                "radiation": {
                    "value": latest.radiation,
                    "delta": delta(latest.radiation, prev.radiation if prev else None),
                    "unit": "W/m²",
                },
                "soil_ec": {
                    "value": latest.soil_ec,
                    "delta": delta(latest.soil_ec, prev.soil_ec if prev else None),
                    "unit": "dS/m",
                },
                "soil_ph": {
                    "value": latest.ph,
                    "delta": delta(latest.ph, prev.ph if prev else None),
                    "unit": "pH",
                },
                "soil_moisture": {
                    "value": latest.soil_moisture,
                    "delta": delta(latest.soil_moisture, prev.soil_moisture if prev else None),
                    "unit": "%",
                },
                "recorded_at": self._fmt_datetime(latest.recorded_at),
            }
        finally:
            db.close()

    def get_crop_status(self, batch_id: int):
        db = SessionLocal()
        try:
            latest = self._get_latest_growth_row(db, batch_id)

            if not latest:
                return {
                    "plant_height": None,
                    "leaf_count": None,
                    "leaf_length": None,
                    "leaf_width": None,
                    "recorded_at": None,
                }

            return {
                "plant_height": latest.plant_height,
                "leaf_count": latest.leaf_count,
                "leaf_length": latest.leaf_length,
                "leaf_width": latest.leaf_width,
                "recorded_at": self._fmt_datetime(latest.recorded_at),
            }
        finally:
            db.close()

    def get_device_logs(self, batch_id: int, limit: int = 4):
        db = SessionLocal()
        try:
            logs = (
                db.query(ActionLog)
                .filter(ActionLog.batch_id == batch_id)
                .order_by(ActionLog.id.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": log.id,
                    "time": self._fmt_time(log.recorded_at),
                    "recorded_at": self._fmt_datetime(log.recorded_at),
                    "device": log.action_type,
                    "detail": log.message,
                    "status": log.status,
                    "mode": log.action_mode,
                }
                for log in logs
            ]
        finally:
            db.close()

    def get_ai_reports(self, batch_id: int, limit: int = 20):
        db = SessionLocal()
        try:
            rows = (
                db.query(AIResult)
                .filter(AIResult.batch_id == batch_id)
                .order_by(AIResult.id.desc())
                .limit(limit)
                .all()
            )

            results = []
            for row in rows:
                level = "추천"
                if (row.severity or 0) >= 3:
                    level = "경고"

                results.append({
                    "id": row.id,
                    "level": level,
                    "title": f"{row.result_type}: {row.result_value}",
                    "time": self._fmt_time(row.recorded_at or row.inferred_at),
                    "recorded_at": self._fmt_datetime(row.recorded_at or row.inferred_at),
                    "confidence": row.confidence,
                    "severity": row.severity,
                    "result_type": row.result_type,
                    "result_value": row.result_value,
                })

            return results
        finally:
            db.close()

    def get_cctv_status(self, batch_id: int):
        return {
            "camera_name": f"{batch_id}번 배치 카메라",
            "stream_status": "connecting"
        }

    def get_overview(self, batch_id: int):
        db = SessionLocal()
        try:
            env = self._get_latest_environment_row(db, batch_id)
            prev_env = self._get_previous_environment_row(db, batch_id)
            growth = self._get_latest_growth_row(db, batch_id)
            ai = self._get_latest_ai_row(db, batch_id)
            issue_count = self._get_recent_issue_count(db, batch_id)

            target_height = 90.0

            growth_progress = 0

            if growth and growth.plant_height:
                growth_progress = round(
                min((growth.plant_height / target_height) * 100, 100),
                1
            )

            env_score = 0
            
            if env:
                env_score += self._score_range(env.temperature, 20, 26, 15)
                env_score += self._score_range(env.humidity, 55, 75, 10)
                env_score += self._score_range(env.co2, 700, 1200, 10)
                env_score += self._score_range(env.radiation, 200, 800, 10)
                env_score += self._score_range(env.soil_ec, 1.0, 2.5, 8)
                env_score += self._score_range(env.ph, 5.5, 6.5, 7)
            else:
                env_score = 30

            growth_score = 0
            if growth:
                growth_score += 8 if growth.plant_height and growth.plant_height > 0 else 3
                growth_score += 6 if growth.leaf_count and growth.leaf_count > 0 else 2
                growth_score += 6 if growth.leaf_length and growth.leaf_length > 0 else 2
                growth_score += 5 if growth.leaf_width and growth.leaf_width > 0 else 2
            else:
                growth_score = 12

            ai_adjust = 0
            if ai:
                severity = ai.severity or 0
                confidence = ai.confidence or 0

                if ai.result_type == "disease" and confidence >= 0.8:
                    ai_adjust -= min(15, severity * 4)
                elif ai.result_type in ["harvest", "flowering"] and confidence >= 0.8:
                    ai_adjust += 3

            issue_penalty = min(issue_count * 2, 10)

            raw_score = env_score + growth_score + ai_adjust - issue_penalty
            score = int(self._clamp(raw_score, 0, 100))
            

            delta_percent = 0
            if env and prev_env:
                current_env_score = (
                    self._score_range(env.temperature, 20, 26, 15)
                    + self._score_range(env.humidity, 55, 75, 10)
                    + self._score_range(env.co2, 700, 1200, 10)
                    + self._score_range(env.radiation, 200, 800, 10)
                    + self._score_range(env.soil_ec, 1.0, 2.5, 8)
                    + self._score_range(env.ph, 5.5, 6.5, 7)
                )
                prev_env_score = (
                    self._score_range(prev_env.temperature, 20, 26, 15)
                    + self._score_range(prev_env.humidity, 55, 75, 10)
                    + self._score_range(prev_env.co2, 700, 1200, 10)
                    + self._score_range(prev_env.radiation, 200, 800, 10)
                    + self._score_range(prev_env.soil_ec, 1.0, 2.5, 8)
                    + self._score_range(prev_env.ph, 5.5, 6.5, 7)
                )
                delta_percent = round(current_env_score - prev_env_score, 1)

            if score >= 90:
                summary = "작물 활력도 최상"
            elif score >= 75:
                summary = "전반적으로 안정적"
            elif score >= 60:
                summary = "일부 관리 필요"
            else:
                summary = "즉시 점검 필요"

            phase = "분석중"
            if growth:
                if (growth.leaf_count or 0) < 5:
                    phase = "초기 생장기"
                elif (growth.leaf_count or 0) < 12:
                    phase = "영양 생장기"
                else:
                    phase = "개화기/생식기"
            

            return {
    "score": score,
    "phase": phase,
    "summary": summary,
    "delta_percent": delta_percent,
    "env_score": round(env_score, 1),
    "growth_score": round(growth_score, 1),
    "ai_adjust": ai_adjust,
    "issue_penalty": issue_penalty,
    "growth_progress": growth_progress,
    "target_height": target_height,
    "updated_at": self._fmt_datetime(env.recorded_at if env else None),
}
        finally:
            db.close()
            

    def get_dashboard(self, batch_id: int):
        return {
            "overview": self.get_overview(batch_id),
            "sensors": self.get_latest_sensors(batch_id),
            "device_logs": self.get_device_logs(batch_id),
            "crop_status": self.get_crop_status(batch_id),
            "ai_reports": self.get_ai_reports(batch_id),
            "cctv": self.get_cctv_status(batch_id),
            "growthDelta": self.get_growth_delta(batch_id),
        }
    def get_growth_delta(self, batch_id: int):
        db = SessionLocal()
        try:
            # 가장 최근(오늘) 초장 데이터 조회
            latest = self._get_latest_growth_row(db, batch_id)
            if not latest or not latest.plant_height:
                return {"day": 0.0, "week": 0.0, "month": 0.0}

            current_height = latest.plant_height
            now = datetime.now()

            # 과거 데이터 조회 헬퍼 함수
            def get_past_height(days_ago):
                target_date = now - timedelta(days=days_ago)
                past_record = (
    db.query(PlantGrowth)
    .filter(
        PlantGrowth.batch_id == batch_id,
        PlantGrowth.recorded_at <= target_date,
    )
    .order_by(PlantGrowth.recorded_at.desc(), PlantGrowth.id.desc())
    .first()
)
                # 과거 기록이 없으면 그냥 현재 키와 같다고 처리(성장량 0)
                return past_record.plant_height if past_record and past_record.plant_height else current_height

            # 어제(1일), 1주(7일), 1달(30일) 전 키 가져오기
            yesterday_height = get_past_height(1)
            week_height = get_past_height(7)
            month_height = get_past_height(30)

            # 차이(Delta) 계산해서 소수점 1자리로 리턴
            return {
                "day": round(current_height - yesterday_height, 1),
                "week": round(current_height - week_height, 1),
                "month": round(current_height - month_height, 1)
            }
        finally:
            db.close()
            