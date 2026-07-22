import requests
import json
import os
from datetime import datetime, timezone, timedelta

# 天文台 API
HKO_API = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"

def get_hko_pressure():
    try:
        res = requests.get(HKO_API, timeout=10).json()
        pressure_data = res.get('meanSeaLevelPressure', {}).get('data', [])
        
        # 尋找京士柏氣壓
        for d in pressure_data:
            if d.get('place') == "京士柏":
                return float(d.get('value'))
                
        print("⚠️ 警告：在天文台 API 中找不到『京士柏』氣壓數據")
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
        print(f"✅ [{time_str}] 成功寫入氣壓: {pressure} hPa 到 Firebase！")
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
