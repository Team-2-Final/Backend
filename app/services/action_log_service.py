from app.db.oracle import SessionLocal
from app.models.oracle.action_log import ActionLog


class ActionLogService:

    def save(
        self,
        batch_id: int,
        action_type: str,
        action_mode: str,
        is_on: str = None,   # ✅ 추가
        metric: str = None,  # ✅ 추가 (너 control_service에서 쓰고 있음)
        trigger_value=None,
        threshold=None,
        status="issued",
        message=None,
    ):
        db = SessionLocal()

        try:

            log = ActionLog(
                batch_id=batch_id,
                action_type=action_type,
                action_mode=action_mode,

                # ✅ 추가 필드
                is_on=is_on,
                metric=metric,

                trigger_value=trigger_value,
                threshold=threshold,
                status=status,
                message=message,
            )

            db.add(log)
            db.commit()
            db.refresh(log)   # 🔥 안전 (id 보장)

            return log.id

        except Exception as e:
            db.rollback()
            print(f"[ActionLog SAVE ERROR] batch={batch_id}, error={e}")
            return None

        finally:
            db.close()

    def update_status(self, log_id: int, status: str, message: str = None):
        db = SessionLocal()

        try:
            log = db.query(ActionLog).filter(ActionLog.id == log_id).first()

            if log:
                log.status = status

                if message is not None:
                    log.message = message

                db.commit()

            return True

        finally:
            db.close()



    EVENT_TYPES = {"disease", "harvest", "flowering"}

    # 디바이스 로그만 조회
    def get_device_logs(self, batch_id: int, limit: int = 6):
        db = SessionLocal()
        try:
            logs = (
                db.query(ActionLog)
                .filter(ActionLog.batch_id == batch_id)
                .filter(~ActionLog.action_type.in_(self.EVENT_TYPES))  # 🔥 이벤트 제외
                .order_by(ActionLog.recorded_at.desc())
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

    # 이벤트 로그만 조회
    def get_event_logs(self, batch_id: int, limit: int = 6):
        db = SessionLocal()
        try:
            logs = (
                db.query(ActionLog)
                .filter(ActionLog.batch_id == batch_id)
                .filter(ActionLog.action_type.in_(self.EVENT_TYPES))  # 🔥 이벤트만
                .order_by(ActionLog.recorded_at.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": log.id,
                    "time": self._fmt_time(log.recorded_at),
                    "recorded_at": self._fmt_datetime(log.recorded_at),
                    "type": log.action_type,
                    "detail": log.message,
                }
                for log in logs
            ]
        finally:
            db.close()    

    def _fmt_datetime(self, dt):
        if not dt:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    
    def _fmt_time(self, dt):
        if not dt:
            return None
    
        from datetime import datetime
    
        now = datetime.now()
    
        try:
            if dt.date() == now.date():
                return dt.strftime("%H:%M")
        except Exception:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    
        return dt.strftime("%m-%d %H:%M")    