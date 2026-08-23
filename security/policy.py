"""
模組名稱：安全與政策防護
說明：嚴格遵守 Public Layer 邊界，限制不合法的抓取與敏感憑證儲存。
"""

class SecurityPolicy:
    ALLOWED_DOMAINS = ["cwa.gov.tw", "taipower.com.tw"]
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        return any(domain in url for domain in cls.ALLOWED_DOMAINS)
    
    @classmethod
    def sanitize_payload(cls, data: dict) -> dict:
        # 確保不帶入任何私有金鑰或個資
        sanitized = {k: v for k, v in data.items() if "token" not in k.lower() and "key" not in k.lower()}
        return sanitized

