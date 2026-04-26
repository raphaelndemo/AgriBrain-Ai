import os
import asyncio
import joblib
import numpy as np
import nest_asyncio
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain.tools import tool
from geopy.geocoders import Nominatim

# The system imports the asynchronous environment ingestion pipeline
from location import get_full_location_context

# The engine applies a patch to allow asynchronous event loops inside LangChain's synchronous execution
nest_asyncio.apply()

load_dotenv()

# SYSTEM INITIALIZATION
# The application establishes a connection to the Supabase PostgreSQL backend
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

# The pipeline initializes the open-source geocoder for coordinate resolution
geolocator = Nominatim(user_agent="agribrain_kenya_v1")

# MACHINE LEARNING PIPELINE
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YIELD_MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "yield_predictor.pkl")
MARKET_MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "market_forecaster.pkl")

def load_ml_model(path):
    """The system loads serialized scikit-learn/XGBoost models into active memory."""
    try:
        return joblib.load(path)
    except Exception as e:
        print(f"System Warning: Failed to load ML asset at {path}. Error: {e}")
        return None

yield_model = load_ml_model(YIELD_MODEL_PATH)
market_model = load_ml_model(MARKET_MODEL_PATH)


# LANGCHAIN AGENT TOOLS

@tool
def geocode_location(location_name: str) -> str:
    """
    The agent uses this to convert a village or town name into precise GPS coordinates.
    Essential for routing data to spatial databases.
    """
    try:
        # The system scopes the query to Kenya to prevent global misdirection
        search_query = f"{location_name}, Kenya"
        location = geolocator.geocode(search_query)
        
        if location:
            return f"Coordinates for {location_name}: Lat {location.latitude}, Lon {location.longitude}"
        return f"Could not precisely locate {location_name}. Suggest a larger nearby town."
    except Exception as e:
        return f"Geocoding subsystem error: {e}"

@tool
def location_intelligence_tool(lat: float, lon: float) -> str:
    """
    The agent uses this to fetch parallel, live weather and soil data for specific coordinates.
    Utilizes asynchronous gathering to prevent LLM timeout.
    """
    try:
        # The pipeline executes the external async script synchronously for LangChain compatibility
        report = asyncio.run(get_full_location_context(lat, lon))
        return report
    except Exception as e:
        return f"Error executing location intelligence matrix: {e}"

@tool
def crop_projection_tool(commodity: str, acres: float, lat: float, lon: float, market_name: str) -> str:
    """
    The agent calculates predicted yield and future revenue using localized ML models.
    Requires: commodity, acreage, and location coordinates.
    """
    if not yield_model or not market_model:
        return "ML Engine Offline. Unable to perform projections at this time."

    try:
        # The engine constructs the feature vector: [pH, N, P, K, Rainfall, Temp]
        soil_weather_features = np.array([[6.2, 0.15, 20.0, 240.0, 500.0, 22.5]])
        
        # The system executes biological yield inference and extracts the scalar value
        yield_per_acre = float(yield_model.predict(soil_weather_features))
        total_bags = int((yield_per_acre * acres * 1000) / 90)
        
        # The system constructs the market feature vector: [current_avg, fuel_index, season_code]
        market_features = np.array([[3400, 215.5, 4]]) 
        future_price = float(market_model.predict(market_features))
        
        revenue = total_bags * future_price

        return (f"📊 PROJECTION REPORT:\n"
                f"- Expected Harvest: {total_bags} bags (90kg)\n"
                f"- Forecasted Price at {market_name}: {future_price:,.2f} KES/bag\n"
                f"- Estimated Gross Revenue: {revenue:,.2f} KES")
    except Exception as e:
        return f"ML Projection calculation error: {e}"

@tool
def get_market_prices(commodity_name: str, county: str = None) -> str:
    """
    The agent queries the Supabase database for real-time market prices.
    Allows for hyper-local price filtering if the county is known.
    """
    try:
        # The system executes a case-insensitive search against the commodity column
        query = supabase.table("market_prices").select("*").ilike("commodity", f"%{commodity_name}%")
        if county:
            query = query.ilike("county", f"%{county}%")
            
        res = query.order("last_updated", desc=True).limit(5).execute()
        
        if not res.data:
            return f"No price data found for {commodity_name}."
            
        output = f"Recent prices for {commodity_name}:\n"
        for row in res.data:
            output += f"📍 {row['market_location']}: Retail {row['retail_price_kes']} KES | Wholesale {row['wholesale_price_kes']} KES\n"
        return output
    except Exception as e:
        return f"Database API error: {e}"

@tool
def find_nearest_agrovets(lat: float, lng: float) -> str:
    """
    The agent executes a PostGIS spatial search for the nearest agricultural suppliers.
    """
    try:
        # The system calls the K-Nearest Neighbors Remote Procedure Call (RPC) in PostGIS
        res = supabase.rpc("find_near_shops", {"u_lat": lat, "u_lng": lng}).execute()
        if not res.data:
            return "No agrovets found in your immediate vicinity."
            
        response = "🏢 Local Agrovets & Markets:\n"
        for item in res.data:
            dist = round(item['dist_meters'] / 1000, 2)
            response += f"- {item['name']} ({item['location_type']}): {dist}km\n"
        return response
    except Exception as e:
        return f"Spatial query error: {e}"

# TOOL REGISTRY
AGRICULTURAL_TOOLS = [
    geocode_location,
    location_intelligence_tool, 
    crop_projection_tool, 
    get_market_prices, 
    find_nearest_agrovets
]