from fastapi import APIRouter

# 🔹 schema
from app.schemas.control.control import DeviceModeRequest, DeviceTargetRequest
from app.services.action_log_service import ActionLogService
from app.db.oracle import SessionLocal
from app.models.oracle.action_log import ActionLog
from app.core.state import device_emergency_map

# 🔹 상태 저장 (메모리)
from app.core.state import (
    latest_action_map,
    device_state_map
)

router = APIRouter()

action_log_service = ActionLogService()

# =========================
# 🔁 모드 변경 (auto / manual)
# =========================
@router.post("/device/mode/{batch_id}")
def set_device_mode(batch_id: int, req: DeviceModeRequest):

    if batch_id not in device_state_map:
        device_state_map[batch_id] = {}

    if req.device not in device_state_map[batch_id]:
        device_state_map[batch_id][req.device] = {}

    device_state_map[batch_id][req.device]["mode"] = req.mode

    if req.mode == "auto":
        device_state_map[batch_id][req.device]["target"] = None

        if batch_id in device_emergency_map:
            device_emergency_map[batch_id][req.device] = False

    return {"device": req.device, "mode": req.mode}


# =========================
# 🎛 수동 제어 설정
# =========================
@router.post("/device/target/{batch_id}")
def set_device_target(batch_id: int, req: DeviceTargetRequest):

    if batch_id not in device_state_map:
        device_state_map[batch_id] = {}

    if req.device not in device_state_map[batch_id]:
        device_state_map[batch_id][req.device] = {}

    device_state_map[batch_id][req.device]["target"] = req.value

    return {"device": req.device, "target": req.value}


# =========================
# ⚙️ 현재 action 조회 (시뮬용)
# =========================
@router.get("/action/{batch_id}")
def get_action(batch_id: int):

    data = latest_action_map.get(batch_id)

    if not data:
        return {"action": {}, "log_id": None}

    log_ids = data.get("log_ids", [])

    # 🔥 하나씩 pop (FIFO)
    next_log_id = log_ids.pop(0) if log_ids else None

    # 상태 갱신
    data["log_ids"] = log_ids
    latest_action_map[batch_id] = data

    return {
        "action": data.get("action", {}),
        "log_id": next_log_id
    }

# ack : 명령이 시뮬에 제대로 받아들여져서 작동했나 확인하고 update
@router.post("/ack/{batch_id}")
def ack_action(batch_id: int, data: dict):

    log_id = data.get("log_id")
    status = data.get("status")
    message = data.get("message")

    if not log_id:
        return {"status": "fail", "message": "log_id missing"}

    action_log_service.update_status(
        log_id=log_id,
        status=status,
        message=message
    )

    return {"status": "ok"}



# =========================
# 🚨 긴급 정지
# =========================
@router.post("/emergency/{batch_id}/{device}")
def set_emergency(batch_id: int, device: str, is_stop: bool):

    # batch 없으면 초기화
    if batch_id not in device_emergency_map:
        device_emergency_map[batch_id] = {}

    device_emergency_map[batch_id][device] = is_stop

    return {
        "batch_id": batch_id,
        "device": device,
        "emergency": is_stop
    }