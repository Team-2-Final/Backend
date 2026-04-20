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
    """
    토마토 지하재배(실내/밀폐형) 기준 실시간 센서 스트림.

    설계 기준
    - 광주기: 16시간 점등 / 8시간 소등
    - radiation 컬럼은 자연 일사량이 아니라 'LED 광량(PPFD 유사값)'로 해석
    - 과실형 토마토의 비교적 보수적인 제어 범위를 반영
    """

    np.random.seed(seed)

    if start_time is None:
        current_time = datetime.now().replace(microsecond=0)
    elif isinstance(start_time, str):
        current_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
    else:
        current_time = start_time.replace(microsecond=0)

    # 초기값: 지하 토마토 재배실이 이미 안정화된 상태를 가정
    temperature = 21.5
    humidity = 66.0
    co2 = 820.0
    radiation = 0.0  # LED off 상태에서 시작해도 자연스럽게 수렴하도록

    water_supply = 1.05
    water_drain = 0.82
    ec_supply = 2.25
    ec_drain = 2.12
    ph_supply = 5.85
    ph_drain = 6.02

    # 하드 제한 범위: 토마토 지하재배용
    TEMP_HARD_MIN, TEMP_HARD_MAX = 16.0, 28.0
    HUM_MIN, HUM_MAX = 50.0, 85.0
    CO2_MIN, CO2_MAX = 450.0, 1200.0
    LIGHT_MIN, LIGHT_MAX = 0.0, 450.0   # PPFD 유사값(umol m-2 s-1 느낌의 운영 범위)
    EC_MIN, EC_MAX = 1.8, 2.8
    PH_MIN, PH_MAX = 5.4, 6.4

    while True:
        hour = current_time.hour

        # 16시간 점등 / 8시간 소등
        # 예: 06:00 ~ 22:00 점등
        lights_on = 6 <= hour < 22

        if lights_on:
            # 점등 중: 토마토 생육 + 착과/광합성 + 수분수정 안정성 고려
            target_temp = 23.8
            target_humidity = 60.0
            target_co2 = 900.0
            target_light = 320.0
            target_water_supply = 1.20
            target_ec_supply = 2.30
            target_ec_drain = 2.15
            target_ph_supply = 5.80
            target_ph_drain = 6.00
        else:
            # 소등 중: 과도한 냉각은 피하고, 습도는 약간 높아지되 너무 높지 않게
            target_temp = 19.2
            target_humidity = 68.0
            target_co2 = 700.0
            target_light = 0.0
            target_water_supply = 0.72
            target_ec_supply = 2.20
            target_ec_drain = 2.05
            target_ph_supply = 5.90
            target_ph_drain = 6.05

        target_water_drain = target_water_supply * 0.78

        # 지하 재배는 외부 기상영향이 적어서 변화는 비교적 완만
        temperature += (target_temp - temperature) * 0.020 + np.random.normal(0, 0.025)
        humidity += (target_humidity - humidity) * 0.022 + np.random.normal(0, 0.10)
        co2 += (target_co2 - co2) * 0.025 + np.random.normal(0, 2.5)
        radiation += (target_light - radiation) * 0.11 + np.random.normal(0, 5.0)

        water_supply += (target_water_supply - water_supply) * 0.030 + np.random.normal(0, 0.008)
        water_drain += (target_water_drain - water_drain) * 0.030 + np.random.normal(0, 0.008)

        ec_supply += (target_ec_supply - ec_supply) * 0.020 + np.random.normal(0, 0.0025)
        ec_drain += (target_ec_drain - ec_drain) * 0.020 + np.random.normal(0, 0.0025)

        ph_supply += (target_ph_supply - ph_supply) * 0.018 + np.random.normal(0, 0.003)
        ph_drain += (target_ph_drain - ph_drain) * 0.018 + np.random.normal(0, 0.003)

        # 이상 상황: 토마토 지하재배실에서 실제로 말이 되는 이벤트 위주
        if anomaly and np.random.rand() < 0.012:
            event_type = np.random.choice([
                "hvac_temp_up",
                "dehumidifier_fail",
                "co2_tank_low",
                "led_drop",
                "fertigation_ec_up",
                "irrigation_drop"
            ])

            if event_type == "hvac_temp_up":
                temperature += np.random.uniform(0.8, 1.8)

            elif event_type == "dehumidifier_fail":
                humidity += np.random.uniform(5.0, 10.0)

            elif event_type == "co2_tank_low":
                co2 -= np.random.uniform(100.0, 220.0)

            elif event_type == "led_drop" and lights_on:
                radiation -= np.random.uniform(80.0, 160.0)

            elif event_type == "fertigation_ec_up":
                ec_supply += np.random.uniform(0.12, 0.28)
                ec_drain += np.random.uniform(0.08, 0.20)

            elif event_type == "irrigation_drop":
                water_supply -= np.random.uniform(0.15, 0.35)
                water_drain -= np.random.uniform(0.08, 0.20)

        # 현실 범위 제한
        temperature = np.clip(temperature, TEMP_HARD_MIN, TEMP_HARD_MAX)
        humidity = np.clip(humidity, HUM_MIN, HUM_MAX)
        co2 = np.clip(co2, CO2_MIN, CO2_MAX)
        radiation = np.clip(radiation, LIGHT_MIN, LIGHT_MAX)

        water_supply = np.clip(water_supply, 0.35, 2.20)
        water_drain = np.clip(water_drain, 0.20, 1.90)

        ec_supply = np.clip(ec_supply, EC_MIN, EC_MAX)
        ec_drain = np.clip(ec_drain, EC_MIN - 0.1, EC_MAX)

        ph_supply = np.clip(ph_supply, PH_MIN, PH_MAX)
        ph_drain = np.clip(ph_drain, PH_MIN, PH_MAX)

        row = {
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": round(float(temperature), 2),
            "humidity": round(float(humidity), 2),
            "co2": round(float(co2), 2),
            "radiation": round(float(radiation), 2),
            "water_supply": round(float(water_supply), 2),
            "water_drain": round(float(water_drain), 2),
            "ec_supply": round(float(ec_supply), 2),
            "ec_drain": round(float(ec_drain), 2),
            "ph_supply": round(float(ph_supply), 2),
            "ph_drain": round(float(ph_drain), 2),
        }

        yield row
        current_time += timedelta(seconds=interval_seconds)


def send_realtime_to_fastapi(
    api_url,
    start_time=None,
    interval_seconds=1,
    anomaly=False,
    max_rows=None,
    timeout=5
):
    """
    1초마다 1개씩 토마토 지하재배 환경 데이터를 생성해서 FastAPI endpoint로 POST 전송.
    """
    stream = environment_sensor_stream_tomato_underground(
        start_time=start_time,
        interval_seconds=interval_seconds,
        anomaly=anomaly
    )

    count = 0
    print(f"토마토 지하재배 환경 실시간 전송 시작 -> {api_url}")

    try:
        while True:
            row = next(stream)

            try:
                response = requests.post(api_url, json=row, timeout=timeout)
                print(f"[{count + 1}] 전송 완료 | status={response.status_code} | data={row}")
            except requests.RequestException as e:
                print(f"[{count + 1}] 전송 실패 | error={e} | data={row}")

            count += 1
            if max_rows is not None and count >= max_rows:
                print("지정된 개수만큼 전송 완료")
                break

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\\n사용자 종료(Ctrl+C)")


if __name__ == "__main__":
    send_realtime_to_fastapi(
        api_url="http://127.0.0.1:8000/api/environment",
        start_time=None,
        interval_seconds=1,
        anomaly=True,
        max_rows=10
    )
