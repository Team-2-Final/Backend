from fastapi import APIRouter

# 🔹 schema
from app.schemas.control.control import DeviceModeRequest, DeviceTargetRequest
from app.services.action_log_service import ActionLogService
from app.db.oracle import SessionLocal
from app.models.oracle.action_log import ActionLog

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
# 📋 현재 목표 수치 설정 조회
# =========================
@router.get("/device-state/{batch_id}")
def get_device_state(batch_id: int):
    state = device_state_map.get(batch_id, {})

    default_devices = {
        "heater": {"mode": "auto", "target": 22.0},
        "humidifier": {"mode": "auto", "target": 65},
        "light": {"mode": "auto", "target": 80},
        "irrigation": {"mode": "auto", "target": 2.5},
        "fertigation": {"mode": "auto", "target": 1.2},
        "co2_gen": {"mode": "manual", "target": 800},
    }

    result = {}
    for device, default_value in default_devices.items():
        current = state.get(device, {})
        result[device] = {
            "mode": current.get("mode", default_value["mode"]),
            "target": current.get("target", default_value["target"]),
        }

    return {
        "batch_id": batch_id,
        "devices": result
    }


# =========================
# ⚙️ 현재 action 조회 (시뮬용)
# =========================
@router.get("/action/{batch_id}")
def get_action(batch_id: int):

    data = latest_action_map.get(batch_id)

    if not data:
        return {"action": {}, "log_id": None}

    return {
        "action": data.get("action", {}),
        "log_id": data.get("log_id")
    }

# ack : 명령이 시뮬에 제대로 받아들여져서 작동했나 확인하고 update
@router.post("/ack/{batch_id}")
def ack_action(batch_id: int, data: dict):
    """
    simulator가 실행 결과 전달
    data:
      - log_id
      - status (applied / failed)
      - message (optional)
    """

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
# 📝 운영 기록 조회
# =========================
@router.get("/logs/{batch_id}")
def get_control_logs(batch_id: int):
    db = SessionLocal()
    try:
        logs = (
            db.query(ActionLog)
            .filter(ActionLog.batch_id == batch_id)
            .order_by(ActionLog.id.desc())
            .limit(20)
            .all()
        )

        return [
            {
                "id": log.id,
                "device": log.action_type,
                "mode": log.action_mode,
                "status": log.status,
                "message": log.message,
            }
            for log in logs
        ]
    finally:
        db.close()


# =========================
# 🚨 긴급 정지
# =========================
@router.post("/device/stop/{batch_id}")
def stop_device(batch_id: int, data: dict):
    device = data.get("device")

    if not device:
        return {"status": "fail", "message": "device missing"}

    if batch_id not in device_state_map:
        device_state_map[batch_id] = {}

    if device not in device_state_map[batch_id]:
        device_state_map[batch_id][device] = {}

    device_state_map[batch_id][device]["mode"] = "manual"
    device_state_map[batch_id][device]["target"] = 0

    log_id = action_log_service.save(
        batch_id=batch_id,
        action_type=device,
        action_mode="manual",
        trigger_value=None,
        threshold=None,
        status="issued",
        message=f"{device} emergency stop"
    )

    return {
        "status": "ok",
        "device": device,
        "mode": "manual",
        "target": 0,
        "log_id": log_id
    }