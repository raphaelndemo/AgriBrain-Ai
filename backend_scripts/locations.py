import os
import time
import asyncio
import httpx
from dotenv import load_dotenv
from pathlib import Path

# LOAD ENVIRONMENT VARIABLES
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


# TOKEN 
_token_cache = {"access_token": None, "expires_at": 0}

#
# data cleaning
def extract_mean_value(raw_json, property_name):
    try:
        data_list = raw_json.get("property", {}).get(property_name, [])
        if not data_list:
            return None

        value = data_list.get("value", {}).get("value")

        # Fix pH scaling 
        if property_name == "ph" and value is not None and value > 14:
            return round(value / 10.0, 2)

        return value

    except (IndexError, KeyError, TypeError):
        return None


# AUTHENTICATION
async def get_valid_token(client):
    now = time.time() * 1000

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

        print("ISDA Token refreshed successfully")
        return _token_cache["access_token"]

    except Exception as e:
        print(f"Authentication failed: {e}")
        return None


# FETCH SINGLE SOIL PROPERTY
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


# FETCH ALL SOIL DATA (NPK + pH)
async def fetch_soil_data(lat, lon):
    properties = [
        "ph",
        "nitrogen_total",
        "phosphorous_extractable",
        "potassium_extractable", # Added for complete NPK profile
        "carbon_organic",
        "clay_content"
    ]

    async with httpx.AsyncClient() as client:
        tasks = [fetch_isda_property(client, lat, lon, p) for p in properties]
        raw_responses = await asyncio.gather(*tasks)

        results = {}
        for prop, raw in zip(properties, raw_responses):
            results[prop] = extract_mean_value(raw, prop)

        return results

# WEATHER DATA (OPEN-METEO FORECAST)
async def get_live_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
        "daily": ["precipitation_sum", "uv_index_max"],
        "timezone": "Africa/Nairobi"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            return {
                "temperature": data["current"].get("temperature_2m"),
                "humidity": data["current"].get("relative_humidity_2m"),
                "wind_speed": data["current"].get("wind_speed_10m"),
                "rainfall": sum(data["daily"].get("precipitation_sum",)),
                "uv_index": max(data["daily"].get("uv_index_max",))
            }
    except Exception as e:
        print(f"Weather API Error: {e}")
        return {}

# AIR QUALITY DATA (OPEN-METEO AQI)
async def get_air_quality(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["us_aqi"]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return {"aqi": data["current"].get("us_aqi")}
    except Exception as e:
        print(f"Air Quality API Error: {e}")
        return {}

# WRAPPER FUNCTION 
async def get_full_location_context(lat, lon):
    try:
        # Run all three external APIs in parallel so it's lightning fast
        soil_data, weather_data, aqi_data = await asyncio.gather(
            fetch_soil_data(lat, lon),
            get_live_weather(lat, lon),
            get_air_quality(lat, lon)
        )

        # Format the block exactly how the LLM needs to read it
        report = (
            f"[LOCATION ANALYSIS]\n"
            f"Coordinates: Latitude {lat}, Longitude {lon}\n\n"

            f"[SOIL CONDITIONS (0-20cm)]\n"
            f"pH Level: {soil_data.get('ph')}\n"
            f"Nitrogen (N): {soil_data.get('nitrogen_total')} g/kg\n"
            f"Phosphorus (P): {soil_data.get('phosphorous_extractable')} ppm\n"
            f"Potassium (K): {soil_data.get('potassium_extractable')} ppm\n"
            f"Organic Carbon: {soil_data.get('carbon_organic')} g/kg\n"
            f"Clay Content: {soil_data.get('clay_content')}%\n\n"

            f"[LIVE METEOROLOGY & AIR QUALITY]\n"
            f"Temperature: {weather_data.get('temperature')} °C\n"
            f"Relative Humidity: {weather_data.get('humidity')}%\n"
            f"Wind Speed: {weather_data.get('wind_speed')} km/h\n"
            f"7-day Rainfall Forecast: {weather_data.get('rainfall')} mm\n"
            f"Max UV/Sun Index: {weather_data.get('uv_index')}\n"
            f"US Air Quality Index (AQI): {aqi_data.get('aqi')}\n"
        )

        return report

    except Exception as e:
        return f"ERROR RETRIEVING LOCATION DATA: {e}"

# TEST BLOCK
if __name__ == "__main__":
    # Test coordinates (e.g., Juja)
    test_lat = -1.102
    test_lon = 37.013

    print(f"\nRunning AgriBrain Location Test for {test_lat}, {test_lon}...\n")
    result = asyncio.run(get_full_location_context(test_lat, test_lon))
    print(result)