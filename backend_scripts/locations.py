import asyncio
import httpx

async def fetch_local_weather(lat: float, lon: float) -> dict:
    """
    Asynchronously fetches current weather and 7-day forecast from Open-Meteo.
    Includes Phase 2 metrics: wind speed (for pesticide drift) and UV index.
    """
    print(f" Fetching weather for coordinates: {lat}, {lon}...")
    
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,rain"
        f"&daily=precipitation_sum,uv_index_max&timezone=Africa%2FNairobi"
    )
    
    try:
        # We use httpx instead of requests so we don't block the Chainlit UI
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract usable data safely
            current = data.get('current', {})
            daily = data.get('daily', {})
            
            print("Live weather data secured.")
            return {
                "status": "success",
                "temperature": current.get('temperature_2m'),
                "humidity": current.get('relative_humidity_2m'),
                "wind_speed": current.get('wind_speed_10m'),
                "current_rain": current.get('rain'),
                "weekly_rain": sum(daily.get('precipitation_sum', [])),
                "uv_index": max(daily.get('uv_index_max',))
            }
            
    except httpx.HTTPError as e:
        print(f"❌ Weather API Error: {e}")
        return {"status": "error", "message": str(e)}

async def fetch_local_soil(lat: float, lon: float) -> dict:
    """
    Fetches 30m resolution African soil data using the OpenEPI wrapper for iSDAsoil.
    Expanded to pull Nitrogen and Clay content for advanced yield ML.
    """
    print(f" Fetching soil data for coordinates: {lat}, {lon}")
    
    # We ask for pH, total nitrogen, and clay content
    url = f"https://api.openepi.io/soil/property?lat={lat}&lon={lon}&properties=phh2o,nitrogen,clay"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            props = data.get('properties', {})
            
            # The API returns values multiplied by 10 or 100 to save bandwidth
            # We use try/except block just in case the location is over water or missing data
            try:
                soil_ph = props.get('phh2o', {}).get('depths', {}).get('values', {}).get('mean', 60) / 10
                nitrogen = props.get('nitrogen', {}).get('depths', {}).get('values', {}).get('mean', 15) / 100
                clay = props.get('clay', {}).get('depths', {}).get('values', {}).get('mean', 300) / 10
            except AttributeError:
                soil_ph, nitrogen, clay = 6.0, 0.15, 30.0 # Safe Kenyan fallbacks
            
            print("Soil chemistry data secured.")
            return {
                "status": "success",
                "soil_ph": soil_ph,
                "nitrogen": nitrogen,
                "clay_percentage": clay
            }
            
    except httpx.HTTPError as e:
        print(f"❌ Soil API Error: {e}")
        return {"status": "fallback", "soil_ph": 6.0, "nitrogen": 0.15, "clay_percentage": 30.0}

async def get_full_location_context(lat: float, lon: float) -> str:
    """
    The master function called by LangChain. 
    Runs both API fetches in parallel for maximum speed.
    """
    # asyncio.gather fires both requests at the exact same time
    weather, soil = await asyncio.gather(
        fetch_local_weather(lat, lon),
        fetch_local_soil(lat, lon)
    )
    
    return (
        f" **Live Geospatial Context (Lat: {lat}, Lon: {lon})**\n\n"
        f" **Meteorology:** Temp: {weather.get('temperature')}°C | Humidity: {weather.get('humidity')}%\n"
        f" **Wind Speed:** {weather.get('wind_speed')} km/h (Note: >15km/h risks pesticide drift)\n"
        f" **Live Rain:** {weather.get('current_rain')} mm | **7-Day Total:** {weather.get('weekly_rain')} mm\n"
        f" **Max UV Index:** {weather.get('uv_index')}\n"
        f" **Soil Chemistry:** pH {soil.get('soil_ph')}, Nitrogen {soil.get('nitrogen')} g/kg, Clay {soil.get('clay_percentage')}%\n"
    )

# --- TEST THE PARALLEL FUNCTIONS ---
if __name__ == "__main__":
    test_lat, test_lon = -1.1018, 37.0144 
    print("\n--- INITIATING PARALLEL SENSORY TEST ---")
    result = asyncio.run(get_full_location_context(test_lat, test_lon))
    print(result)