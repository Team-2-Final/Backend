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