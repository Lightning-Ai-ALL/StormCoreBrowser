"""
專案名稱：StormCoreBrowser
模組名稱：自動化執行總入口
說明：自動啟動沙得爾颱風數據採集、安全校驗與下游管線推送。
"""

import sys
from pathlib import Path

# 將根目錄加入 path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from security.policy import SecurityPolicy
from collectors.public_source import PublicSourceCollector
from connectors.storm_core import StormCoreConnector

def run_automation():
    print("=== [StormCoreBrowser] 自動化採集代理啟動 ===")
    
    target_url = "https://www.cwa.gov.tw/V8/C/W/TY/TY.html"
    if not SecurityPolicy.validate_url(target_url):
        print(f"安全攔截：網址 {target_url} 不在白名單內")
        return
        
    collector = PublicSourceCollector()
    raw_data = collector.collect("Saudel", target_url)
    
    connector = StormCoreConnector()
    saved_path = connector.deliver_to_raw_layer("TY_SAUDEL_AUTO", asdict(raw_data) if hasattr(raw_data, '__dataclass_fields__') else raw_data.__dict__)
    print(f"成功將沙得爾颱風公開資料交付至 Storm Core: {saved_path}")
    print("=== 自動化寫軟體與數據沉澱執行完畢 ===")

if __name__ == "__main__":
    run_automation()
