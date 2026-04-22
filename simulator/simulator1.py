import time
import requests
import numpy as np
from datetime import datetime, timedelta


def environment_sensor_stream_tomato_underground(
    start_time=None,
    interval_seconds=1,
    anomaly=False,
    seed=42
):

    np.random.seed(seed)

    if start_time is None:
        current_time = datetime.now().replace(microsecond=0)
    else:
        current_time = start_time.replace(microsecond=0)

    # 초기값
    temperature = 19.5
    humidity = 55.0
    co2 = 770.0
    radiation = 0.0

    soil_ec = 2.0
    soil_moisture = 31.0
    ph = 5.9

    action = None

    # 제한
    TEMP_MIN, TEMP_MAX = 16, 28
    HUM_MIN, HUM_MAX = 50, 85
    CO2_MIN, CO2_MAX = 450, 1200

    while True:
        hour = current_time.hour
        lights_on = 6 <= hour < 22

        # 목표값
        target_temp = 24 if lights_on else 19
        target_hum = 60 if lights_on else 70
        target_co2 = 900 if lights_on else 700

        # =========================
        # 🔥 자연 변화 (action 없을 때만)
        # =========================
        if not action:
            temperature += (target_temp - temperature) * 0.02 + np.random.normal(0, 0.03)
            humidity += (target_hum - humidity) * 0.02 + np.random.normal(0, 0.15)
            co2 += (target_co2 - co2) * 0.02 + np.random.normal(0, 3)

            soil_moisture -= np.random.uniform(0.1, 0.3)
            soil_ec -= np.random.uniform(0.01, 0.03)

        # =========================
        # 🔥 제어 반영 (핵심)
        # =========================
        if action:

            # 🌡 온도
            if action.get("heater"):
                temperature += 0.8
            elif action.get("cooler"):
                temperature -= 0.8

            # 🌬 환풍기
            if action.get("fan"):
                temperature = max(temperature - 0.5, 10)   # 최저 10도
                humidity = max(humidity - 2.0, 20)        # 최저 20%
                co2 = max(co2 - 50, 300) # 최저 300ppm

            # 💧 물주기
            if action.get("irrigation"):
                soil_moisture += 4.0
            else:
                soil_moisture -= np.random.uniform(0.1, 0.3)

            # ⚡ 양분
            if action.get("fertigation"):
                soil_ec += 0.2
            else:
                soil_ec -= np.random.uniform(0.01, 0.03)

            # 💨 가습
            if action.get("humidifier"):
                humidity += 2.5

            # 🌫 CO2
            if action.get("co2_gen"):
                co2 += 80

        # 광량 (시간 기반)
        radiation = 320 if lights_on else 0

        # 제한
        temperature = np.clip(temperature, TEMP_MIN, TEMP_MAX)
        humidity = np.clip(humidity, HUM_MIN, HUM_MAX)
        co2 = np.clip(co2, CO2_MIN, CO2_MAX)
        soil_moisture = np.clip(soil_moisture, 0, 100)
        soil_ec = np.clip(soil_ec, 0, 5)

        row = {
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": round(float(temperature), 2),
            "humidity": round(float(humidity), 2),
            "co2": round(float(co2), 2),
            "radiation": float(radiation),
            "soil_ec": round(float(soil_ec), 2),
            "soil_moisture": round(float(soil_moisture), 2),
            "ph": round(float(ph), 2),
        }

        # 👉 action 받기
        action = yield row

        # current_time += timedelta(seconds=interval_seconds)
        current_time += timedelta(hours=2)


# =========================
# 🔥 실행부
# =========================
def run_simulator(api_url, batch_id):

    stream = environment_sensor_stream_tomato_underground()
    row = next(stream)

    count = 0

    last_log_id = None

    while True:
        count += 1

        row["batch_id"] = batch_id

        try:
            # 1️⃣ 환경 전송
            requests.post(f"{api_url}/environment/{batch_id}", json=row, timeout=5)

            # 2️⃣ action + log_id 받기 (한 번만!)
            resp = requests.get(
                f"{api_url}/control/action/{batch_id}",
                timeout=5
            ).json()

            log_id = resp.get("log_id")
            action = resp.get("action", {})

        except Exception as e:
            print("API 오류:", e)
            log_id = None
            action = {}

        print(f"\n[{count}] batch={batch_id}")
        print("ENV:", row)
        print("LOG_ID:", log_id)
        print("ACTION:", action)

        # 3️⃣ action 반영 (이거 필수)
        row = stream.send(action)

        # 4️⃣ ACK (실행 결과 반영)
        if log_id and log_id != last_log_id:
            try:
                requests.post(
                    f"{api_url}/control/ack/{batch_id}",
                    json={
                        "log_id": log_id,
                        "status": "applied",
                        "message": None
                    },
                    timeout=5
                )
                last_log_id = log_id   # 🔥 여기 중요

            except Exception as e:
                print("ACK 실패:", e)

        time.sleep(2)


if __name__ == "__main__":
    run_simulator("http://127.0.0.1:8000/api", batch_id=1)