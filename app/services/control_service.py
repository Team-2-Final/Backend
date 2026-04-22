# app/services/control_service.py

from app.core.state import device_state_map

# =========================
# STATE (히스테리시스용)
# =========================
last_state = {}


# =========================
# AUTO RULES (히스테리시스 적용)
# =========================
AUTO_RULES = [
    {"key": "fan", "metric": "temperature", "on": 26, "off": 24},
    {"key": "cooler", "metric": "temperature", "on": 26, "off": 24},
    {"key": "heater", "metric": "temperature", "on": 20, "off": 22},
    {"key": "humidifier", "metric": "humidity", "op": "<", "th": 55},
    {"key": "co2_gen", "metric": "co2", "op": "<", "th": 700},
    {"key": "irrigation", "metric": "soil_moisture", "op": "<", "th": 30},
    {"key": "fertigation", "metric": "soil_ec", "op": "<", "th": 2.2},
]


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

    for rule in AUTO_RULES:
        if evaluate(rule, env, last_state):
            key = rule["key"]
            action[key] = True

            reason[key] = {
                "mode": "auto",
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
            "value": hour
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
            action["fan"] = env["temperature"] > target

        # -------- 습도 --------
        elif device == "humidifier":
            action["humidifier"] = env["humidity"] < target

        # -------- CO2 --------
        elif device == "co2_gen":
            action["co2_gen"] = env["co2"] < target

        # -------- 관수 --------
        elif device == "irrigation":
            action["irrigation"] = bool(target)

        # -------- 양액 --------
        elif device == "fertigation":
            action["fertigation"] = bool(target)

        

        reason[device] = {
            "mode": "manual",
            "value": env.get(device if device in env else None),
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

    # =========================
    # 5. STATE 업데이트
    # =========================
    last_state = action.copy()

    return action, reason