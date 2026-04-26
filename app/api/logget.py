from fastapi import APIRouter
from app.services.action_log_service import ActionLogService

router = APIRouter(prefix="/action-logs", tags=["action-logs"])

service = ActionLogService()

@router.get("/{batch_id}")
def get_logs(batch_id: int, type: str = "device", limit: int = 6):
    if type == "event":
        return service.get_event_logs(batch_id=batch_id, limit=limit)
    else:
        return service.get_device_logs(batch_id=batch_id, limit=limit)