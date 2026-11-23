import math
import time
from datetime import datetime, timezone, timedelta
import requests
import firebase_admin
from firebase_admin import credentials, firestore

# 1. 初始化 Firebase (沿用你原本的憑證設定)
# cred = credentials.Certificate("serviceAccountKey.json")
# firebase_admin.initialize_app(cred)
db = firestore.client()

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

def main():
    pressure, temp, humidity, dew_point = fetch_hk_weather()

    hk_tz = timezone(timedelta(hours=8))
    now_hk = datetime.now(hk_tz)
    timestamp_ms = int(time.time() * 1000)
    time_str = now_hk.strftime("%m/%d %H:%M")

    doc_data = {
        "pressure": pressure,
        "temp": temp,
        "humidity": humidity,
        "dewPoint": dew_point,
        "timestamp": timestamp_ms,
        "timeStr": time_str
    }

    db.collection("barometer_history").add(doc_data)
    print(f"[{time_str}] Saved -> P: {pressure} hPa | T: {temp}°C | RH: {humidity}% | Td: {dew_point}°C")

if __name__ == "__main__":
    main()
