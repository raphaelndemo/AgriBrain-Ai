import os
import math
import joblib
import numpy as np
import pandas as pd
from langchain.tools import tool
from geopy.geocoders import Nominatim
from supabase import create_client, Client
from dotenv import load_dotenv
from backend_engine.location import get_full_location_context # Import internal modules


# 1. INITIALIZATION SETUP
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

# Initialize the free geocoder for the Investor Land Selection Tool
geolocator = Nominatim(user_agent="agribrain_investor_app")

# Set up paths for ML Models
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YIELD_MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "yield_predictor.pkl")
MARKET_MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "market_forecaster.pkl")

# Load models into global memory once on startup
try:
    print("Loading regression Yield Predictor")
    yield_model = joblib.load(YIELD_MODEL_PATH)
    
    print("Loading xgboost Market Forecaster ")
    market_model = joblib.load(MARKET_MODEL_PATH)
    
    print("All ML Models Loaded Successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not load models. Check paths.\n{e}")
    yield_model = None
    market_model = None



# 2. HELPER FUNCTIONS & ML LOGIC

def calc_dist(lat1, lon1, lat2, lon2):
    """Vectorized Haversine function for distance in km."""
    r = 6371 
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = math.sin(math.radians(lat2 - lat1) / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2)**2
    return r * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def calculate_crop_projection_logic(commodity: str, acres: float, lat: float, lon: float, market_name: str) -> str:
    """
    The engine that feeds live data into the .pkl models.
    """
    if yield_model is None or market_model is None:
        return "ML Models are currently offline. Using estimated averages instead."

    commodity = commodity.lower().strip()

    # YIELD INFERENCE
    # Example Feature Vector: [ph, n, p, k, rainfall, temp]
    yield_features = np.array([[6.5, 0.12, 15.0, 200.0, 450.0, 24.0]]) # Mocked input for now
    
    # Extract scalar from prediction array
    predicted_tonnes_per_acre = float(yield_model.predict(yield_features)[0])
    total_yield_tonnes = predicted_tonnes_per_acre * acres
    total_bags = int((total_yield_tonnes * 1000) / 90) # Standard 90kg Kenyan bag

    # MARKET PRICE INFERENCE 
    # Example Feature Vector: [current_price, fuel_price, chatlog_volume, month]
    market_features = np.array([[3500, 212.0, 450, 4]]) # Mocked input for now
    
    # Extract scalar from prediction array
    predicted_future_price_per_bag = float(market_model.predict(market_features)[0])
    
    # REVENUE & OUTPUT
    total_revenue = total_bags * predicted_future_price_per_bag
    
    return (
        f"[SYSTEM PROJECTION CALCULATION]\n"
        f"Based on real-time soil/weather and your {acres} acres:\n"
        f"- Predicted Yield: ~{total_bags} bags ({total_yield_tonnes:.2f} tonnes)\n"
        f"- Predicted Price at {market_name} (in 3 months): {predicted_future_price_per_bag:,.2f} KES/bag\n"
        f"- Total Estimated Revenue: {total_revenue:,.2f} KES\n"
        f"Deliver this to the farmer with a focus on potential ROI."
    )


# LANGCHAIN LLM TOOLS

@tool
def geocode_location(location_name: str) -> str:
    """
    Use this tool when a user mentions a specific city or town by name (e.g., 'Kitengela', 'Nairobi').
    It converts the name into Latitude and Longitude coordinates.
    """
    try:
        search_query = f"{location_name}, Kenya"
        location = geolocator.geocode(search_query)
        if location:
            return f"Coordinates for {location_name}: Lat {location.latitude}, Lon {location.longitude}"
        else:
            return f"Could not find coordinates for {location_name}. Ask the user for a nearby major town."
    except Exception as e:
        return f"Geocoding failed: {e}"

@tool
def location_intelligence_tool(lat: float, lon: float) -> str:
    """Use this to fetch live Open-Meteo weather and iSDAsoil chemistry (NPK/pH) for a coordinate."""
    return get_full_location_context(lat, lon)

@tool
def crop_projection_tool(commodity: str, acres: float, lat: float, lon: float, market_name: str) -> str:
    """Use this to calculate total bags harvested and expected financial revenue using the ML models."""
    return calculate_crop_projection_logic(commodity, acres, lat, lon, market_name)

@tool
def market_arbitrage_tool(commodity: str, lat: float, lon: float) -> str:
    """Use this to find the best physical market to sell a specific crop within a 50km radius."""
    commodity = commodity.lower().strip()
    
    # Query Supabase for markets and prices
    markets = supabase.table('agrovets_markets').select('*').eq('location_type', 'Market').execute().data
    prices_res = supabase.table('market_prices').select('*').eq('commodity', commodity).execute().data
    
    # Map prices by market location for O(1) lookups
    prices_data = {p['market_location']: p for p in prices_res}
    
    options = []
    for m in markets:
        dist = calc_dist(lat, lon, m['latitude'], m['longitude'])
        if dist <= 50 and m['location_name'] in prices_data:
            price = prices_data[m['location_name']].get('wholesale_price_kes', 'N/A')
            options.append({"market": m['location_name'], "dist": dist, "price": price})
            
    # Sort by distance and take the top 3
    options = sorted(options, key=lambda x: x['dist'])[:3]
    
    if not options:
        return f"No arbitrage options found for {commodity} within 50km."
        
    report = "Arbitrage Options:\n" 
    report += "\n".join([f"- {o['market']} ({o['dist']:.1f} km): {o['price']} KES/kg" for o in options])
    return report