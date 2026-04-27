import os
import time
import asyncio
import httpx
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# ==========================================
# TOKEN CACHE
# ==========================================
_token_cache = {"access_token": None, "expires_at": 0}
_token_lock = asyncio.Lock()


# ==========================================
# DATA CLEANING (PRESERVED LOGIC)
# ==========================================
def extract_mean_value(raw_json, property_name):
    try:
        data_list = raw_json.get("property", {}).get(property_name, [])
        if not data_list:
            return None

        value = data_list[0].get("value", {}).get("value")

        # Fix pH scaling issue
        if property_name == "ph" and value is not None and value > 14:
            return round(value / 10.0, 2)

        return value

    except (IndexError, KeyError, TypeError):
        return None


# ==========================================
# AUTHENTICATION (FIXED: single refresh with lock)
# ==========================================
async def get_valid_token(client):
    now = time.time() * 1000

    # Quick check before acquiring lock
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 30000:
        return _token_cache["access_token"]

    async with _token_lock:
        # Re-check inside lock — another task may have refreshed while we waited
        if _token_cache["access_token"] and now < _token_cache["expires_at"] - 30000:
            return _token_cache["access_token"]

        login_url = os.getenv("ISDA_LOGIN_URL")
        username = os.getenv("isDA_username")
        password = os.getenv("isDA_password")

        if not login_url:
            print("ERROR: ISDA_LOGIN_URL missing in .env")
            return None

        payload = {
            "username": username,
            "password": password
        }

        try:
            response = await client.post(login_url, data=payload, timeout=10.0)
            response.raise_for_status()

            data = response.json()
            _token_cache["access_token"] = data.get("access_token")
            _token_cache["expires_at"] = now + (60 * 60 * 1000)

            print("Token refreshed successfully")
            return _token_cache["access_token"]

        except Exception as e:
            print(f"Authentication failed: {e}")
            return None


# ==========================================
# FETCH SINGLE PROPERTY (PRESERVED LOGIC)
# ==========================================
async def fetch_isda_property(client, lat, lon, property_name):
    token = await get_valid_token(client)
    if not token:
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    params = {
        "lon": lon,
        "lat": lat,
        "depth": "0-20"
    }

    url = "https://api.isda-africa.com/isdasoil/v2/soilproperty"

    try:
        response = await client.get(url, params=params, headers=headers, timeout=15.0)
        response.raise_for_status()
        return response.json()

    except Exception as e:
        print(f"Error fetching {property_name}: {e}")
        return None


# ==========================================
# FETCH ALL SOIL DATA (ASYNC PARALLEL)
# ==========================================
async def fetch_soil_data(lat, lon):
    properties = [
        "ph",
        "nitrogen_total",
        "clay_content",
        "carbon_organic",
        "phosphorous_extractable"
    ]

    async with httpx.AsyncClient() as client:
        tasks = [fetch_isda_property(client, lat, lon, p) for p in properties]
        raw_responses = await asyncio.gather(*tasks)

        results = {}
        for prop, raw in zip(properties, raw_responses):
            results[prop] = extract_mean_value(raw, prop)

        return results


# ==========================================
# WEATHER DATA (OPEN-METEO)
# ==========================================
async def get_live_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m"],
        "daily": ["precipitation_sum"],
        "timezone": "Africa/Nairobi"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            temperature = data["current"]["temperature_2m"]
            rainfall = sum(data["daily"]["precipitation_sum"])

            return {
                "temperature": temperature,
                "rainfall": rainfall
            }

    except Exception as e:
        return {"error": str(e)}


# ==========================================
# MAIN WRAPPER FUNCTION (FOR BOT USE)
# ==========================================
async def get_full_location_context(lat, lon):
    try:
        soil_data, weather_data = await asyncio.gather(
            fetch_soil_data(lat, lon),
            get_live_weather(lat, lon)
        )

        report = {
            "location": {
                "latitude": lat,
                "longitude": lon
            },
            "soil": {
                "ph": soil_data.get("ph"),
                "nitrogen_g_per_kg": soil_data.get("nitrogen_total"),
                "clay_content_percent": soil_data.get("clay_content"),
                "organic_carbon_g_per_kg": soil_data.get("carbon_organic"),
                "phosphorus_ppm": soil_data.get("phosphorous_extractable")
            },
            "weather": {
                "temperature_c": weather_data.get("temperature"),
                "rainfall_7day_mm": weather_data.get("rainfall")
            }
        }

        return json.dumps(report, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


# ==========================================
# TEST BLOCK
# ==========================================
if __name__ == "__main__":
    test_lat = -1.102
    test_lon = 37.013

    print("\nRunning AgriBrain Location Test...\n")
    result = asyncio.run(get_full_location_context(test_lat, test_lon))
    print(result)