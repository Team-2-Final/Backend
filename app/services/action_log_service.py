from app.db.oracle import SessionLocal
from app.models.oracle.action_log import ActionLog


class ActionLogService:

    def save(
        self,
        batch_id: int,
        action_type: str,
        action_mode: str,
        trigger_value=None,
        threshold=None,
        status="issued",   # ✔ 기본값 issued로 변경
        message=None,
    ):
        db = SessionLocal()

        try:
            log = ActionLog(
                batch_id=batch_id,
                action_type=action_type,
                action_mode=action_mode,
                trigger_value=trigger_value,
                threshold=threshold,
                status=status,
                message=message,
            )

            db.add(log)
            db.commit()

            return log.id   # ✔ 중요: 이후 update 위해 id 반환

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
                if message:
                    log.message = message

                db.commit()

            return True

        finally:
            db.close()        