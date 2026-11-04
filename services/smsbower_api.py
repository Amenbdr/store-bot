import requests
import logging

logger = logging.getLogger(__name__)

class SMSBowerService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://smsbower.page/stubs/handler_api.php"
        self.payment_url = "https://smsbower.page/api/payment/getActualWalletAddress"

    def _get(self, params: dict) -> any:
        """دالة مساعدة لإرسال الطلبات للـ API ومعالجة الأخطاء بأمان"""
        params['api_key'] = self.api_key
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            
            # فحص إذا كان الرد نصياً بسيطاً (مثل الأرصدة أو حالات التفعيل)
            text_resp = response.text.strip()
            if text_resp.startswith("BAD_KEY") or text_resp.startswith("BAD_ACTION") or text_resp.startswith("BAD_SERVICE"):
                logger.error(f"SMSBower API Error Response: {text_resp}")
                return None
                
            # محاولة تحويل الرد إلى JSON إذا كان مدعوماً
            try:
                return response.json()
            except ValueError:
                return text_resp
        except Exception as e:
            logger.error(f"HTTP Request failed in SMSBowerService: {e}")
            return None

    def get_balance(self) -> float:
        """جلب رصيد الحساب الحالي من الموقع (getBalance)"""
        res = self._get({"action": "getBalance"})
        if res and isinstance(res, str) and "ACCESS_BALANCE:" in res:
            try:
                return float(res.split(":")[-1])
            except ValueError:
                return 0.0
        return 0.0

    def get_services_list(self) -> list:
        """جلب قائمة الخدمات المتاحة (getServicesList)"""
        res = self._get({"action": "getServicesList"})
        if isinstance(res, dict) and res.get("status") == "success":
            return res.get("services", [])
        return []

    def get_prices(self, service: str, country: str) -> dict:
        """جلب الأسعار والكميات المتقدمة حسب السيرفرات (getPricesV3)"""
        res = self._get({
            "action": "getPricesV3",
            "service": service,
            "country": country
        })
        if isinstance(res, dict):
            return res
        return {}

    def buy_number(self, service: str, country: str, max_price: float = None) -> dict:
        """شراء رقم باستخدام النسخة المحدثة (getNumberV2) مع كامل تفاصيل التفعيل"""
        params = {
            "action": "getNumberV2",
            "service": service,
            "country": country
        }
        if max_price:
            params["maxPrice"] = max_price
            
        res = self._get(params)
        if isinstance(res, dict) and "activationId" in res:
            return {
                "activation_id": str(res.get("activationId")),
                "number": str(res.get("phoneNumber")),
                "cost": float(res.get("activationCost", 0.0)),
                "operator": res.get("activationOperator")
            }
            
        # كآلية احتياطية (Fallback) لو رجع النظام بالشكل النصي القديم getNumber
        if isinstance(res, str) and res.startswith("ACCESS_NUMBER:"):
            parts = res.split(":")
            if len(parts) >= 3:
                return {
                    "activation_id": parts[1],
                    "number": parts[2],
                    "cost": 0.50,
                    "operator": "Default"
                }
        return None

    def get_sms_code(self, activation_id: str) -> str:
        """الاستعلام عن كود التفعيل ورسالة الـ SMS"""
        res = self._get({
            "action": "getStatus",
            "id": activation_id
        })
        if isinstance(res, str):
            if res == "STATUS_WAIT_CODE" or res == "WAITING":
                return "WAITING"
            elif res.startswith("STATUS_OK:"):
                return res.split(":")[-1]
        return None

    def cancel_activation(self, activation_id: str) -> bool:
        """إلغاء الرقم واسترداد القيمة"""
        res = self._get({
            "action": "setStatus",
            "status": 8,  # كود الإلغاء في النظام
            "id": activation_id
        })
        return res == "ACCESS_CANCEL" or (isinstance(res, str) and "CANCEL" in res)

    def get_wallet_address(self, coin: str = "usdt", network: str = "tron") -> str:
        """جلب عنوان المحفظة الثابتة للإيداع (getActualWalletAddress)"""
        try:
            params = {
                "api_key": self.api_key,
                "coin": coin,
                "network": network
            }
            response = requests.get(self.payment_url, params=params, timeout=15)
            data = response.json()
            return data.get("wallet_address")
        except Exception as e:
            logger.error(f"Failed to get wallet address: {e}")
            return None
