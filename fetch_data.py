import os
import json
import math
import time
from datetime import datetime, timezone, timedelta
import requests

# 📍 1. 填入你的 Firebase Project ID（從截圖看應為 "hko-barometer"）
FIREBASE_PROJECT_ID = "hko-barometer"

# 若環境變數裡有存 firebaseConfig JSON，會自動覆蓋讀取 projectId
for key in ["FIREBASE_CONFIG", "FIREBASE_CREDENTIALS", "FIREBASE_SERVICE_ACCOUNT", "FIREBASE_KEY"]:
    val = os.environ.get(key)
    if val and "projectId" in val:
        try:
            cfg = json.loads(val.strip())
            if cfg.get("projectId"):
                FIREBASE_PROJECT_ID = cfg["projectId"]
                break
        except Exception:
            pass

# 2. 計算露點溫度 (Magnus-Tetens Formula)
def calculate_dew_point(temp_c, rh):
    a = 17.625
    b = 243.04
    alpha = math.log(rh / 100.0) + (a * temp_c) / (b + temp_c)
    dew_point = (b * alpha) / (a - alpha)
    return round(dew_point, 1)

# 3. 從 Open-Meteo 獲取香港即時海平面氣壓、氣溫 (2m) 與相對濕度 (2m)
def fetch_hk_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=22.3193&longitude=114.1694"
        "&current=pressure_msl,temperature_2m,relative_humidity_2m"
        "&timezone=Asia%2FHong_Kong"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    current = resp.json()["current"]

    pressure = round(float(current["pressure_msl"]), 2)
    temp = round(float(current["temperature_2m"]), 1)
    humidity = round(float(current["relative_humidity_2m"]), 0)
    dew_point = calculate_dew_point(temp, humidity)

    return pressure, temp, humidity, dew_point

# 4. 透過 Firestore REST API 直接寫入數據
def save_to_firestore(pressure, temp, humidity, dew_point, timestamp_ms, time_str):
    firestore_url = (
        f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
        f"/databases/(default)/documents/barometer_history"
    )

    payload = {
        "fields": {
            "pressure": {"doubleValue": float(pressure)},
            "temp": {"doubleValue": float(temp)},
            "humidity": {"integerValue": str(int(humidity))},
            "dewPoint": {"doubleValue": float(dew_point)},
            "timestamp": {"integerValue": str(int(timestamp_ms))},
            "timeStr": {"stringValue": time_str}
        }
    }

    resp = requests.post(firestore_url, json=payload, timeout=15)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Firestore 寫入失敗 ({resp.status_code}): {resp.text}")

def main():
    pressure, temp, humidity, dew_point = fetch_hk_weather()

    hk_tz = timezone(timedelta(hours=8))
    now_hk = datetime.now(hk_tz)
    timestamp_ms = int(time.time() * 1000)
    time_str = now_hk.strftime("%m/%d %H:%M")

    save_to_firestore(pressure, temp, humidity, dew_point, timestamp_ms, time_str)
    print(f"[{time_str}] Saved -> P: {pressure} hPa | T: {temp}°C | RH: {humidity}% | Td: {dew_point}°C")

if __name__ == "__main__":
    main()
