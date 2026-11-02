import os
import json
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database.json")

DEFAULT_PRICES = {
    "pubg_60": 1.0,
    "pubg_325": 5.0,
    "ff_100": 1.0,
    "ff_310": 3.0
}

DEFAULT_COUNTRIES = {
    "🇺🇸 أمريكا": {"price": 1.5, "stock": 10},
    "🇬🇧 بريطانيا": {"price": 2.0, "stock": 5}
}

def load_db():
    if not os.path.exists(DB_FILE):
        initial_data = {
            "users": {}, 
            "coupons": {}, 
            "prices": DEFAULT_PRICES, 
            "countries": DEFAULT_COUNTRIES, 
            "verified": {}
        }
        save_db(initial_data)
        return initial_data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "users" not in data: data["users"] = {}
            if "coupons" not in data: data["coupons"] = {}
            if "prices" not in data: data["prices"] = DEFAULT_PRICES
            if "countries" not in data: data["countries"] = DEFAULT_COUNTRIES
            if "verified" not in data: data["verified"] = {}
            return data
    except Exception as e:
        logging.error(f"Error loading DB: {e}")
        return {
            "users": {}, 
            "coupons": {}, 
            "prices": DEFAULT_PRICES, 
            "countries": DEFAULT_COUNTRIES, 
            "verified": {}
        }

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving DB: {e}")
