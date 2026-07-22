import requests
import json
import os
from datetime import datetime, timezone, timedelta

# 使用 Open-Meteo API 獲取香港（京士柏座標 22.3119, 114.1708）的即時海平面氣壓
OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast?latitude=22.3119&longitude=114.1708&current=sea_level_pressure"

def get_pressure():
    try:
        # 1. 優先嘗試 Open-Meteo API (全球 CDN，穩定不擋 IP)
        res = requests.get(OPEN_METEO_API, timeout=10)
        if res.status_code == 200:
            data = res.json()
            p = data.get('current', {}).get('sea_level_pressure')
            if p:
                print(f"✅ 成功從 Open-Meteo 獲取香港海平面氣壓: {p} hPa")
                return float(p)

    except Exception as e:
        print(f"⚠️ Open-Meteo 擷取失敗: {e}")

    # 2. 備用方案：嘗試香港天文台 API
    try:
        hko_url = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(hko_url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            mslp = data.get('meanSeaLevelPressure', {}).get('data', [])
            for item in mslp:
                if item.get('value'):
                    val = float(item.get('value'))
                    print(f"✅ 成功從香港天文台獲取氣壓: {val} hPa")
                    return val
    except Exception as e:
        print(f"⚠️ 天文台 API 擷取失敗: {e}")

    return None

def save_to_firestore(pressure):
    # 從 GitHub Secrets 取得 Firebase 配置
    raw_config = os.environ.get('FIREBASE_CONFIG')
    if not raw_config:
        print("❌ 錯誤：找不到 FIREBASE_CONFIG 環境變數，請檢查 GitHub Secrets 設定！")
        exit(1)
        
    try:
        firebase_config = json.loads(raw_config)
        project_id = firebase_config.get('projectId')
    except Exception as e:
        print(f"❌ 錯誤：FIREBASE_CONFIG JSON 解析失敗: {e}")
        exit(1)

    # 建立目前時間戳記 (HKT UTC+8)
    hkt = timezone(timedelta(hours=8))
    now = datetime.now(hkt)
    timestamp_ms = int(now.timestamp() * 1000)
    time_str = now.strftime("%m/%d %H:%M")

    # Firestore REST API URL
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
        print(f"🎉 [{time_str}] 成功寫入氣壓: {pressure} hPa 到 Firebase！")
    else:
        print(f"❌ 寫入 Firestore 失敗 (HTTP {response.status_code}): {response.text}")
        exit(1)

if __name__ == "__main__":
    p = get_pressure()
    if p is not None:
        save_to_firestore(p)
    else:
        print("❌ 無法獲取任何有效的氣壓值，終止本次寫入。")
        exit(1)
