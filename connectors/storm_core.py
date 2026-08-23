"""
模組名稱：Storm Core 銜接器
說明：負責將採集到的結構化資料安全對接至下游 Storm-Core-Taiwan-Shader 專案的 RAW 層。
"""

import json
from pathlib import Path

class StormCoreConnector:
    def __init__(self, target_dir: str = "./storm_core_storage/RAW"):
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
    def deliver_to_raw_layer(self, event_id: str, payload: dict) -> str:
        file_path = self.target_dir / f"{event_id}_raw.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)
        return str(file_path)

