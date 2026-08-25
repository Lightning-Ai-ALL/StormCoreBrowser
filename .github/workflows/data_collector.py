#StormCore瀏覽器/.github/workflows/data_collector.py python3
# -*- coding: utf-8 -*-
"""
data_collector.py - 安全擷取 CWA 公開資料（雨量／天氣）
支援：
- 本地 RAW 儲存（預設路徑可設定）
- 重試、429/401 處理、快取
- 可選 Webhook 推送（僅通知，不傳送金鑰）
- 輸出 JSON 格式含來源標記，符合 Shader RAW 規範
"""

import os
import json
import hashlib
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dotenv import load_dotenv

load_dotenv()  # 載入 .env（請勿提交）

# ===== 設定區 =====
CWA_API_KEY = os.getenv("CWA_API_KEY")          # 必填
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
# 輸出目錄（請調整為您的私人 Shader 路徑，或使用相對路徑）
RAW_STORAGE = Path(os.getenv("RAW_STORAGE", "./data/RAW"))
RAW_STORAGE.mkdir(parents=True, exist_ok=True)

# Webhook（可選，若無則設為 None）
WEBHOOK_URL = os.getenv("WEBHOOK_URL", None)

# 建議的沙德爾颱風期間 dataset_id（可從外部 JSON 載入）
DEFAULT_DATASETS = [
    "O-A0002-001",   # 雨量站觀測資料
    "O-A0001-001",   # 天氣觀測資料
    "F-D0047-091",   # 颱風路徑預測（若仍有效）
]

# 快取目錄（避免重複請求）
CACHE_DIR = Path("./.cache")
CACHE_DIR.mkdir(exist_ok=True)

# ===== 核心函數 =====

def fetch_cwa_safe(dataset_id: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """
    安全呼叫 CWA API，含重試、錯誤處理、快取。
    """
    if not CWA_API_KEY:
        raise ValueError("CWA_API_KEY 未設定，請檢查 .env")

    # 建立快取鍵
    cache_key = hashlib.md5(f"{dataset_id}_{json.dumps(params or {}, sort_keys=True)}".encode()).hexdigest()
    cache_path = CACHE_DIR / f"{cache_key}.json"

    # 若快取存在且未過期（例如保留 1 小時）
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 3600:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

    url = f"{CWA_BASE_URL}/{dataset_id}"
    headers = {"Accept": "application/json"}
    params = params or {}
    params["Authorization"] = CWA_API_KEY

    retries = 3
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 401:
                print(f"❌ 授權失敗，請檢查 CWA_API_KEY")
                return None
            if resp.status_code == 429:
                wait = (attempt + 1) * 2
                print(f"⚠️ 速率限制，等待 {wait} 秒")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            # 儲存快取
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except requests.exceptions.RequestException as e:
            print(f"⚠️ 請求失敗（嘗試 {attempt+1}/{retries}）: {e}")
            time.sleep(1)
    return None

def save_to_raw(dataset_id: str, data: Dict, source_note: str = "CWA") -> Path:
    """
    將擷取結果寫入 RAW_STORAGE，並附加來源標記。
    檔案命名：{dataset_id}_{timestamp}.json
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{dataset_id}_{timestamp}.json"
    filepath = RAW_STORAGE / filename

    # 加入中繼資料（來源、時間、dataset_id）
    enriched = {
        "source": source_note,
        "dataset_id": dataset_id,
        "collected_at": datetime.utcnow().isoformat() + "Z",
        "data": data
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print(f"✅ 已寫入 RAW: {filepath}")
    return filepath

def notify_webhook(filepath: Path, dataset_id: str):
    """可選 Webhook 通知（僅通知檔案路徑與 dataset，不傳送金鑰）"""
    if not WEBHOOK_URL:
        return
    payload = {
        "event": "new_raw_data",
        "dataset_id": dataset_id,
        "file": str(filepath),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        r.raise_for_status()
        print(f"📨 Webhook 推送成功")
    except Exception as e:
        print(f"⚠️ Webhook 推送失敗: {e}")

# ===== 主程式（範例） =====

def collect_datasets(dataset_list: List[str] = None):
    if dataset_list is None:
        dataset_list = DEFAULT_DATASETS

    for ds_id in dataset_list:
        print(f"🔄 開始收集 {ds_id} ...")
        data = fetch_cwa_safe(ds_id)
        if data:
            filepath = save_to_raw(ds_id, data, source_note="CWA_StormCore")
            notify_webhook(filepath, ds_id)
        else:
            print(f"⚠️ 無法取得 {ds_id} 資料，跳過")

if __name__ == "__main__":
    # 可從命令列參數或環境變數讀取 dataset 清單
    import sys
    if len(sys.argv) > 1:
        collect_datasets(sys.argv[1:])
    else:
        collect_datasets()
