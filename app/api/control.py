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

    if batch_id not in device_emergency_map:
        device_emergency_map[batch_id] = {}

    if batch_id not in device_state_map:
        device_state_map[batch_id] = {}

    if device not in device_state_map[batch_id]:
        device_state_map[batch_id][device] = {}

    device_emergency_map[batch_id][device] = is_stop

    if is_stop:
        device_state_map[batch_id][device]["mode"] = "emergency"
        device_state_map[batch_id][device]["target"] = None
    else:
        device_state_map[batch_id][device]["mode"] = "auto"
        device_state_map[batch_id][device]["target"] = None

    action_log_service.save(
        batch_id=batch_id,
        action_type=device,
        action_mode="emergency",
        is_on="off",
        metric=None,
        trigger_value=None,
        threshold=None,
        status="triggered",
        message="관리자 긴급 정지 실행",
    )

    return {
        "batch_id": batch_id,
        "device": device,
        "emergency": is_stop
    }

@router.get("/device-state/{batch_id}")
def get_device_state(batch_id: int):
    return {
        "devices": device_state_map.get(batch_id, {}),
        "emergency": device_emergency_map.get(batch_id, {})
    }

@router.get("/logs/{batch_id}")
def get_control_logs(batch_id: int):
    db = SessionLocal()
    try:
        logs = (
            db.query(ActionLog)
            .filter(ActionLog.batch_id == batch_id)
            .order_by(ActionLog.recorded_at.desc())
            .limit(6)
            .all()
        )



        return [
    {
        "id": log.id,
        "time": log.recorded_at.strftime("%H:%M") if log.recorded_at else "-",
        "device": log.action_type,
        "mode": log.action_mode,
        "is_on": log.is_on,
        "metric": log.metric,
        "value": log.trigger_value,
        "threshold": log.threshold,
        "status": log.status,
        "message": log.message or make_device_message(log),
    }
    for log in logs
]
    finally:
        db.close()
    
def make_device_message(log):
    name = {
        "co2_gen": "CO2 농도",
        "light": "광량",
        "fertigation": "양액 농도",
        "irrigation": "토양 수분",
        "fan": "CO2 농도",
        "heater": "온도",
        "cooler": "온도",
        "humidifier": "습도",
    }.get(log.action_type, log.action_type)

    is_on = str(log.is_on or "").lower()

    if is_on == "on":
        return f"{name} 조절을 위해 장치 가동"

    if is_on == "off":
        return f"{name} 안정화로 장치 정지"

    return f"{name} 제어 상태 변경"