import requests
import json
import os
from datetime import datetime, timezone, timedelta

# 香港京士柏座標，精確請求 pressure_msl (海平面氣壓)
URL_OPEN_METEO = "https://api.open-meteo.com/v1/forecast?latitude=22.3119&longitude=114.1708&current=pressure_msl"

def fetch_pressure():
    print("🌐 正在發送請求至 Open-Meteo API...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(URL_OPEN_METEO, headers=headers, timeout=15)
        print(f"📡 API 回應狀態碼: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            p = data.get('current', {}).get('pressure_msl')
            if p is not None:
                print(f"✅ 成功擷取到香港海平面氣壓: {p} hPa")
                return float(p)
            else:
                print("❌ JSON 結構中未找到 pressure_msl 欄位")
        else:
            print(f"❌ API 請求失敗，內容: {res.text[:200]}")
    except Exception as e:
        print(f"❌ 發生 Exception 異常: {e}")

    return None

def save_to_firestore(pressure):
    raw_config = os.environ.get('FIREBASE_CONFIG')
    if not raw_config:
        print("❌ 錯誤：找不到 FIREBASE_CONFIG 環境變數，請檢查 GitHub Secrets！")
        exit(1)
        
    try:
        firebase_config = json.loads(raw_config)
        project_id = firebase_config.get('projectId')
    except Exception as e:
        print(f"❌ 錯誤：FIREBASE_CONFIG JSON 解析失敗: {e}")
        exit(1)

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
        print(f"🎉 [{time_str}] 成功寫入氣壓: {pressure} hPa 到 Firebase！")
    else:
        print(f"❌ 寫入 Firestore 失敗 (HTTP {response.status_code}): {response.text}")
        exit(1)

if __name__ == "__main__":
    p = fetch_pressure()
    if p is not None:
        save_to_firestore(p)
    else:
        print("❌ 無法獲取任何有效的氣壓值，終止本次寫入。")
        exit(1)
