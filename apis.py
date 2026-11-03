import requests
from database import get_setting

class SMSBowerAPI:
    BASE_URL = "https://smsbower.app/stubs/handler_api.php"

    @staticmethod
    def _get_key():
        """جلب مفتاح الـ API المخزن مسبقاً في قاعدة البيانات بواسطة المشرف"""
        return get_setting("smsbower_api_key", "")

    @classmethod
    def get_balance(cls) -> str:
        """جلب رصيد الحساب الحالي من موقع SMSBower"""
        api_key = cls._get_key()
        if not api_key:
            return "0.0 (المفتاح غير مسجل)"
        
        params = {
            "api_key": api_key,
            "action": "getBalance"
        }
        try:
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            data = response.text.strip()
            if "ACCESS_BALANCE" in data:
                return data.split(":")[1]
            return "0.0"
        except:
            return "0.0"

    @classmethod
    def get_prices_and_stock(cls, service: str):
        """
        جلب الأسعار والمخزون لكل الدول للخدمة المحددة من الموقع مباشرة
        باستخدام المفتاح المحفوظ في قاعدة البيانات
        """
        api_key = cls._get_key()
        if not api_key:
            return {}
            
        params = {
            "api_key": api_key,
            "action": "getPrices",
            "service": service
        }
        try:
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            return response.json()
        except Exception:
            return {}

    @classmethod
    def get_countries_list(cls):
        """جلب قائمة الدول المتاحة وأكوادها من الموقع"""
        api_key = cls._get_key()
        if not api_key:
            return {}
            
        params = {
            "api_key": api_key,
            "action": "getCountriesList"
        }
        try:
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            return response.json()
        except:
            return {}

    @classmethod
    def buy_number(cls, service: str, country: int):
        """شراء رقم جديد لخدمة معينة ودولة معينة"""
        api_key = cls._get_key()
        if not api_key:
            return "ERROR: API Key not set"
            
        params = {
            "api_key": api_key,
            "action": "getNumber",
            "service": service,
            "country": country
        }
        try:
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            return response.text.strip()
        except Exception as e:
            return f"ERROR: {str(e)}"

    @classmethod
    def get_sms_code(cls, activation_id: str):
        """جلب كود التفعيل (SMS) للرقم الذي تم شراؤه"""
        api_key = cls._get_key()
        if not api_key:
            return "ERROR: API Key not set"
            
        params = {
            "api_key": api_key,
            "action": "getStatus",
            "id": activation_id
        }
        try:
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            return response.text.strip()
        except Exception as e:
            return f"ERROR: {str(e)}"

    @classmethod
    def cancel_number(cls, activation_id: str):
        """إلغاء الرقم واسترداد الرصيد"""
        api_key = cls._get_key()
        if not api_key:
            return "ERROR: API Key not set"
            
        params = {
            "api_key": api_key,
            "action": "setStatus",
            "status": 8,  # كود إلغاء الرقم في السيرفرات
            "id": activation_id
        }
        try:
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            return response.text.strip()
        except Exception as e:
            return f"ERROR: {str(e)}"
