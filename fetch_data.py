import requests
import json
import os
from datetime import datetime, timezone, timedelta

# 香港天文台即時天氣 API
HKO_API = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"

def extract_pressure(data):
    """靈活搜尋 JSON 中的氣壓數據"""
    # 情況 1：標準 meanSeaLevelPressure 結構
    mslp = data.get('meanSeaLevelPressure', {})
    if isinstance(mslp, dict):
        p_list = mslp.get('data', [])
        if isinstance(p_list, list) and len(p_list) > 0:
            for item in p_list:
                if item.get('place') == '京士柏' and item.get('value'):
                    print(f"✅ 成功從 meanSeaLevelPressure 取得京士柏氣壓: {item.get('value')} hPa")
                    return float(item.get('value'))
            # 若無京士柏，取第一筆
            if p_list[0].get('value'):
                print(f"✅ 成功取得 [{p_list[0].get('place')}] 氣壓: {p_list[0].get('value')} hPa")
                return float(p_list[0].get('value'))

    # 情況 2：部分時段直接放在主層級或站點列表中
    if 'pressure' in data and isinstance(data['pressure'], dict):
        p_data = data['pressure'].get('data', [])
        if isinstance(p_data, list) and len(p_data) > 0:
            val = p_data[0].get('value')
            if val:
                print(f"✅ 成功從 pressure 欄位取得氣壓: {val} hPa")
                return float(val)

    return None

def get_hko_pressure():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(HKO_API, headers=headers, timeout=10)
        
        if res.status_code != 200:
            print(f"❌ 天文台 API 回應異常，HTTP 狀態碼: {res.status_code}")
            return None

        data = res.json()
        pressure = extract_pressure(data)
        
        if pressure is not None:
            return pressure

        # 如果即時 API 剛好維護中，備用方案：抓取天文台過去24小時 API
        print("⚠️ 即時 API 暫無氣壓，嘗試切換至過去24小時備用 API...")
        past_api = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=past24hr&lang=tc"
        past_res = requests.get(past_api, headers=headers, timeout=10).json()
        
        past_data = past_res.get('past24hr', [])
        for item in reversed(past_data): # 從最新的一筆開始找
            if item.get('element') == 'meanSeaLevelPressure' and item.get('value'):
                val = float(item.get('value'))
                print(f"✅ 成功從過去24小時 API 取得最後紀錄: {val} hPa")
                return val

        print("❌ 備用 API 亦未找到氣壓數據")
        return None

    except Exception as e:
        print(f"❌ 擷取數據時發生例外狀況: {e}")
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
    p = get_hko_pressure()
    if p is not None:
        save_to_firestore(p)
    else:
        print("❌ 無法獲取任何有效的氣壓值，終止本次寫入。")
        exit(1)
