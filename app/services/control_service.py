# app/services/control_service.py

from app.core.state import device_state_map

# =========================
# STATE (히스테리시스용)
# =========================
last_state = {}

axis_lock = {
    "co2": {},          # batch_id별로 관리해야 함
    "temperature": {}
}



# =========================
# AUTO RULES (히스테리시스 적용)
# =========================
AUTO_RULES = [
    {"key": "fan", "metric": "co2", "on": 900, "off": 800},
    {"key": "cooler", "metric": "temperature", "on": 26, "off": 24},
    {"key": "heater", "metric": "temperature", "on": 20, "off": 22},
    {"key": "humidifier", "metric": "humidity", "op": "<", "th": 55},
    {"key": "co2_gen", "metric": "co2", "op": "<", "th": 700},
    {"key": "irrigation", "metric": "soil_moisture", "op": "<", "th": 30},
    {"key": "fertigation", "metric": "soil_ec", "op": "<", "th": 2.2},
]

DEVICE_METRIC_MAP = {
    "fan": "co2",
    "cooler": "temperature",
    "heater": "temperature",
    "humidifier": "humidity",
    "co2_gen": "co2",
    "irrigation": "soil_moisture",
    "fertigation": "soil_ec",
}


# =========================
# RULE 평가
# =========================
def evaluate(rule, env, state):
    key = rule["key"]
    val = env.get(rule["metric"])
    prev = state.get(key, False)

    if val is None:
        return False

    # 히스테리시스
    if "on" in rule:
        if val >= rule["on"]:
            return True
        elif val <= rule["off"]:
            return False
        else:
            return prev

    # 일반 룰
    op = rule["op"]
    th = rule["th"]

    if op == ">":
        return val > th
    elif op == "<":
        return val < th
    elif op == "eq":
        return val == th

    return False


# =========================
# MAIN
# =========================
def decide_action(env: dict, batch_id: int):

    global last_state

    # batch별 state 가져오기
    state = last_state.get(batch_id, {})
    # =========================
    # 1. 기본 action (AUTO)
    # =========================
    action = {
        "fan": False,
        "irrigation": False,
        "fertigation": False,
        "humidifier": False,
        "heater": False,
        "cooler": False,
        "co2_gen": False,
        "light": False,
    }

    reason = {}

    # =========================
    # 🔥 0. LOCK 먼저 확정
    # =========================
    device_state = device_state_map.get(batch_id, {})

    for device, state in device_state.items():
        mode = state.get("mode")

        # auto → lock 해제
        if mode == "auto":
            if device in ["fan", "co2_gen"]:
                if axis_lock["co2"].get(batch_id) == device:
                    axis_lock["co2"][batch_id] = None

            if device in ["heater", "cooler"]:
                if axis_lock["temperature"].get(batch_id) == device:
                    axis_lock["temperature"][batch_id] = None

        # manual → lock 설정
        if mode == "manual":
            if device in ["fan", "co2_gen"]:
                axis_lock["co2"][batch_id] = device

            if device in ["heater", "cooler"]:
                axis_lock["temperature"][batch_id] = device

    # 🔥 확정된 lock
    co2_lock = axis_lock["co2"].get(batch_id)
    temp_lock = axis_lock["temperature"].get(batch_id)

    for rule in AUTO_RULES:

        key = rule["key"]

        # 🔥 CO2 LOCK
        if key in ["fan", "co2_gen"] and co2_lock:
            if key != co2_lock:
                continue

        # 🔥 TEMPERATURE LOCK
        if key in ["heater", "cooler"] and temp_lock:
            if key != temp_lock:
                continue


        if evaluate(rule, env, state):
            key = rule["key"]
            action[key] = True

            reason[key] = {
                "mode": "auto",
                "metric": rule.get("metric"),
                "value": env.get(rule.get("metric")),
                "target": rule.get("on") or rule.get("th")
            }

    # =========================
    # 2. LIGHT (시간 기반)
    # =========================
    if "timestamp" in env:
        hour = int(env["timestamp"][11:13])
        action["light"] = 6 <= hour < 22

        # 🔥 이거 추가
        reason["light"] = {
            "mode": "auto",
            "metric": "time",
            "value": hour,
            "target": None
        }

    # =========================
    # 3. DEVICE MANUAL OVERRIDE
    # =========================
    device_state = device_state_map.get(batch_id, {})

    for device, state in device_state.items():

        mode = state.get("mode")
        target = state.get("target")


        # 🔥 manual만 override
        if mode != "manual" or target is None:
            continue


        # -------- 온도 계열 --------
        if device == "heater":
            action["heater"] = env["temperature"] < target

        elif device == "cooler":
            action["cooler"] = env["temperature"] > target

        elif device == "fan":
            action["fan"] = env["co2"] > target

        # -------- 습도 --------
        elif device == "humidifier":
            action["humidifier"] = env["humidity"] < target

        # -------- CO2 --------
        elif device == "co2_gen":
            action["co2_gen"] = env["co2"] < target

        # -------- 관수 --------
        elif device == "irrigation":
            action["irrigation"] = env["soil_moisture"] < target

        # -------- 양액 --------
        elif device == "fertigation":
            action["fertigation"] = env["soil_ec"] < target

        metric = DEVICE_METRIC_MAP.get(device)

        reason[device] = {
            "mode": "manual",
            "metric": metric,
            "value": env.get(metric) if metric else None,
            "target": target
        }

    # =========================
    # 4. 충돌 방지
    # =========================

    # 히터 vs 쿨러
    if action["heater"] and action["cooler"]:
        action["heater"] = False
        reason["heater_blocked"] = {"reason": "cooler_priority"}

    # 팬 vs CO2
    if action["fan"]:
        action["co2_gen"] = False
        reason["co2_blocked"] = {"reason": "fan_running"}

    # 팬 vs 가습기
    if action["fan"]:
        action["humidifier"] = False
        reason["humidifier_blocked"] = {"reason": "fan_running"}
        
    # 🔥 CO2 LOCK 강제
    if axis_lock["co2"].get(batch_id) == "fan":
        action["co2_gen"] = False

    elif axis_lock["co2"].get(batch_id) == "co2_gen":
        action["fan"] = False


    # 🔥 TEMP LOCK 강제
    if axis_lock["temperature"].get(batch_id) == "heater":
        action["cooler"] = False

    elif axis_lock["temperature"].get(batch_id) == "cooler":
        action["heater"] = False    

    # 🔥 DEBUG OUTPUT (여기 추가)
    # =========================
    print("\n================ CONTROL_SERVICE OUTPUT ================")
    print("[ENV]")
    print(env)
    print("\n[ACTION]")
    print(action)
    print("\n[REASON]")
    print(reason)
    print("========================================================\n")

    # 🔥 CO2 unlock
    if axis_lock["co2"].get(batch_id) == "fan" and not action["fan"]:
        axis_lock["co2"][batch_id] = None

    if axis_lock["co2"].get(batch_id) == "co2_gen" and not action["co2_gen"]:
        axis_lock["co2"][batch_id] = None


    # 🔥 TEMP unlock
    if axis_lock["temperature"].get(batch_id) == "heater" and not action["heater"]:
        axis_lock["temperature"][batch_id] = None

    if axis_lock["temperature"].get(batch_id) == "cooler" and not action["cooler"]:
        axis_lock["temperature"][batch_id] = None


    # =========================
    # 5. STATE 업데이트
    # =========================
    last_state[batch_id] = action.copy()

    return action, reason