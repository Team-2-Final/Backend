from fastapi import APIRouter
from datetime import datetime

from app.services.environment_service import EnvironmentService
from app.services.control_service import decide_action
from app.schemas.environment.environment import EnvironmentCreate
from app.services.action_log_service import ActionLogService
from app.services.dashboard_service import DashboardService
from app.schemas.environment.environment import EnvironmentCreate
from app.websocket.manager import ws_manager
import json

from app.core.state import (
    latest_action_map
)

router = APIRouter()

environment_service = EnvironmentService()
action_log_service = ActionLogService()
dashboard_service = DashboardService()


def normalize_action(action: dict):
    if not action:
        return {}
    return {k: bool(v) for k, v in action.items()}


# 환경 정보 받고 db 저장 및 자동 액션 설정 및 액션 저장 
@router.post("/{batch_id}")
async def insert_env(batch_id: int, data: EnvironmentCreate):

    result = await environment_service.save(batch_id, data)

    env_dict = data.model_dump()

    if hasattr(data, "recorded_at") and data.recorded_at:
        env_dict["timestamp"] = data.recorded_at.strftime("%Y-%m-%d %H:%M:%S")
    else:
        env_dict["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 🔥 여기 핵심
    action, reason = decide_action(
        env_dict,
        batch_id=batch_id
    )

    # 🔥 이전 상태 가져오기
    prev_data = latest_action_map.get(batch_id, {})
    prev_action = prev_data.get("action")

    log_id = None

    # 🔥 action 변경 시에만 로그 생성
    if normalize_action(prev_action) != normalize_action(action):

        # mode 판단 (auto / manual / mixed)
        modes = {info.get("mode", "auto") for info in reason.values()}
        action_mode = modes.pop() if len(modes) == 1 else "mixed"

        log_id = action_log_service.save(
            batch_id=batch_id,
            action_type="composite",
            action_mode=action_mode,
            trigger_value=None,
            threshold=None,
            status="issued",
            message=json.dumps({
                "action": action,
                "reason": reason,
                "timestamp": env_dict["timestamp"]
            })
        )

    else:
        # 🔥 이전 log_id 유지 (핵심)
        log_id = prev_data.get("log_id")


    # 🔥 상태 저장
    latest_action_map[batch_id] = {
        "action": action,
        "reason": reason,
        "log_id": log_id
    }
    
    await ws_manager.broadcast(batch_id, {
        "type" : "dashboard_update",
        "type" : dashboard_service.get_dashbard(batch_id)
    })


    return result



