import logging
import requests

logging.basicConfig(level=logging.INFO)

class SMSBowerService:
    API_URL = "https://smsbower.app/stubs/handler_api.php"

    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.cached_countries = {}

    def get_balance(self) -> float | None:
        params = {'api_key': self.api_key, 'action': 'getBalance'}
        try:
            res = requests.get(self.API_URL, params=params, timeout=30).text
            if "ACCESS_BALANCE" in res:
                return float(res.split(":")[1])
            return None
        except Exception as e:
            logging.error(f"[SMSBower] error get_balance: {e}")
            return None

    def get_countries(self) -> dict:
        if self.cached_countries:
            return self.cached_countries
        params = {'api_key': self.api_key, 'action': 'getCountries'}
        try:
            res = requests.get(self.API_URL, params=params, timeout=10).json()
            countries = {}
            items = res if isinstance(res, list) else res.values() if isinstance(res, dict) else []
            for item in items:
                if isinstance(item, dict):
                    c_id = str(item.get('id'))
                    name = item.get('eng') or item.get('rus') or f"Country {c_id}"
                    countries[c_id] = name
            if countries:
                self.cached_countries = countries
            return countries
        except Exception as e:
            logging.error(f"[SMSBower] error get_countries: {e}")
            return {}

    def get_prices(self, service: str, country_id: str | int) -> dict | None:
        params = {
            'api_key': self.api_key,
            'action': 'getPricesV3',
            'service': service,
            'country': str(country_id)
        }
        try:
            res = requests.get(self.API_URL, params=params, timeout=10).json()
            if isinstance(res, dict) and str(country_id) in res:
                c_data = res[str(country_id)]
                if isinstance(c_data, dict) and service in c_data:
                    return c_data[service]
            return None
        except Exception as e:
            logging.error(f"[SMSBower] error get_prices: {e}")
            return None

    def buy_number(self, service: str, country_id: str | int, operator: str = None) -> dict | None:
        params = {
            'api_key': self.api_key,
            'action': 'getNumber',
            'service': service,
            'country': str(country_id)
        }
        if operator and str(operator).lower() not in ["default", "any", "none", "auto", ""] and not str(operator).isdigit():
            params['operator'] = str(operator)
        try:
            res = requests.get(self.API_URL, params=params, timeout=15).text
            if "ACCESS_NUMBER" in res:
                parts = res.split(":")
                return {"activation_id": parts[1], "number": parts[2]}
            return None
        except Exception as e:
            logging.error(f"[SMSBower] error buy_number: {e}")
            return None

    def get_sms_code(self, activation_id: str | int) -> str | None:
        params = {'api_key': self.api_key, 'action': 'getStatus', 'id': str(activation_id)}
        try:
            res = requests.get(self.API_URL, params=params, timeout=10).text
            if "STATUS_OK" in res:
                return res.split(":")[1]
            elif "STATUS_WAIT_CODE" in res:
                return "WAITING"
            return None
        except Exception as e:
            logging.error(f"[SMSBower] error get_sms: {e}")
            return None

    def cancel_activation(self, activation_id: str | int) -> bool:
        params = {'api_key': self.api_key, 'action': 'setStatus', 'status': 8, 'id': str(activation_id)}
        try:
            res = requests.get(self.API_URL, params=params, timeout=10).text
            return "ACCESS_CANCEL" in res or res != ""
        except Exception as e:
            logging.error(f"[SMSBower] error cancel: {e}")
            return False
