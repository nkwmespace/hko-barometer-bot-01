import requests
import json
import os
from datetime import datetime, timezone, timedelta

# 天文台 API
HKO_API = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"

# 氣象站優先順序：京士柏 -> 橫瀾島 -> 赤鱲角
STATION_PRIORITY = ["京士柏", "橫瀾島", "赤鱲角"]

def get_hko_pressure():
    try:
        res = requests.get(HKO_API, timeout=10).json()
        pressure_data = res.get('meanSeaLevelPressure', {}).get('data', [])
        
        # 1. 印出目前 API 有提供的所有站點（方便 Debug）
        available_places = [d.get('place') for d in pressure_data]
        print(f"ℹ️ 天文台當前提供氣壓的站點: {available_places}")

        # 2. 依照優先順序尋找氣象站
        for station in STATION_PRIORITY:
            for d in pressure_data:
                if d.get('place') == station and d.get('value') is not None:
                    print(f"✅ 成功獲取 [{station}] 海平面氣壓: {d.get('value')} hPa")
                    return float(d.get('value'))
                
        # 3. 若優先清單都找不到，取列表第一筆可用的氣壓數據
        if pressure_data and pressure_data[0].get('value') is not None:
            first_station = pressure_data[0].get('place')
            val = float(pressure_data[0].get('value'))
            print(f"⚠️ 優先站點暫無數據，改用第一個可用站點 [{first_station}]: {val} hPa")
            return val

        print("❌ 天文台 API 當前未提供任何氣壓數據")
        return None
    except Exception as e:
        print(f"❌ 擷取天文台數據失敗: {e}")
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
        print(f"❌ 錯誤：FIREBASE_CONFIG JSON 格式解析失敗: {e}")
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
    p = get_hko_pressure()
    if p is not None:
        save_to_firestore(p)
    else:
        print("❌ 未能獲取有效的氣壓值，終止寫入。")
        exit(1)
