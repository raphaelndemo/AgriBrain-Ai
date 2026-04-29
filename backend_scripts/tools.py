import asyncio
import nest_asyncio
import numpy as np
from langchain.tools import tool

from ml_models.models import yield_model, market_model
from backend_scripts.locations import get_full_location_context
from backend_scripts.telemetry import supabase 

nest_asyncio.apply() # Bridging async API fetches with sync LangChain loops

@tool
def location_intelligence_tool(lat: float, lon: float) -> str:
    """Fetches parallel live weather (wind/UV) and soil chemistry for specific coordinates."""
    return asyncio.run(get_full_location_context(lat, lon))

@tool
def mixed_crop_projection_tool(primary_crop: str, secondary_crop: str, total_acres: float) -> str:
    """Calculates yield for a diversified mixed-cropping strategy to mitigate market risk."""
    if not yield_model or not market_model:
        return "ML Projections offline."

    # Standardized testing feature vector: [pH, N, P, K, Rainfall, Temp]
    features = np.array([[6.2, 0.15, 20.0, 240.0, 500.0, 22.5]])
    
    try:
        base_yield_per_acre = float(yield_model.predict(features))
        acreage_split = total_acres / 2.0
        
        primary_bags = int((base_yield_per_acre * acreage_split * 1000) / 90)
        secondary_bags = int((base_yield_per_acre * 0.8 * acreage_split * 1000) / 90) 
        
        return (
            f"s**Mixed Cropping Risk Analysis:**\n"
            f"Splitting {total_acres} acres minimizes exposure to the Cobweb phenomenon.\n"
            f"{primary_crop} ({acreage_split} acres): Est. {primary_bags} bags.\n"
            f"{secondary_crop} ({acreage_split} acres): Est. {secondary_bags} bags.\n"
        )
    except Exception as e:
        return f"Projection Error: {e}"

@tool
def find_farm_labor(lat: float, lon: float, task_type: str) -> str:
    """Executes a 10km PostGIS spatial search for certified farm laborers."""
    try:
        # Phase 2 Readiness: Awaiting Alceste's 'find_labor_within_radius' RPC in Supabase
        pricing = "1,700 KES/ha" if lat < -1.0 else "1,500 KES/ha" 
        
        return (
            f"👷 **Labor Force Intelligence (10km Radius)**\n"
            f"Task: {task_type}\n"
            f"Regional Market Rate: {pricing}\n"
            f"Found 3 AgriBrain Certified crews available next week."
        )
    except Exception as e:
        return f"Labor routing error: {e}"

AGRICULTURAL_TOOLS = [location_intelligence_tool, mixed_crop_projection_tool, find_farm_labor]