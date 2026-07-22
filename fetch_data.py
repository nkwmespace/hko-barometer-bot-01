import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta

# 1. 天文台 API
HKO_API = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"

# 2. 初始化 Firebase (這裡使用環境變數取得金鑰，或直接使用 Service Account)
# 為簡化範例，使用 Firebase REST API 寫入，或使用 firebase-admin 庫
import json
import os

# 從 GitHub Secrets 取得 Firebase 配置
firebase_config = json.loads(os.environ['FIREBASE_CONFIG'])
project_id = firebase_config['projectId']

def get_hko_pressure():
    res = requests.get(HKO_API).json()
    kp_data = next((d for d in res['meanSeaLevelPressure']['data'] if d['place'] == "京士柏"), None)
    if kp_data:
        return float(kp_data['value'])
    return None

def save_to_firestore(pressure):
    # 使用 Firestore REST API 免去繁瑣的金鑰設定
    # 建立目前時間戳記 (HKT UTC+8)
    hkt = timezone(timedelta(hours=8))
    now = datetime.now(hkt)
    timestamp_ms = int(now.timestamp() * 1000)
    time_str = now.strftime("%m/%d %H:%M")

    url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/barometer_history"
    
    payload = {
        "fields": {
            "timestamp": {"integerValue": timestamp_ms},
            "timeStr": {"stringValue": time_str},
            "pressure": {"doubleValue": pressure}
        }
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print(f"[{time_str}] 成功寫入氣壓: {pressure} hPa")
    else:
        print("寫入失敗:", response.text)

if __name__ == "__main__":
    p = get_hko_pressure()
    if p:
        save_to_firestore(p)
