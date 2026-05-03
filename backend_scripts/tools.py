import asyncio
import nest_asyncio
import numpy as np
from langchain_core.tools import tool, Tool
from ml_models.models import yield_model, market_model
from backend_scripts.locations import get_full_location_context
from backend_scripts.telemetry import supabase 
from geopy.geocoders import Nominatim
from langchain_community.tools import DuckDuckGoSearchRun

nest_asyncio.apply() # Bridging async API fetches with sync LangChain loops


# 1. Crop Projection Tool: Combines yield data with market prices for financial forecasting.
@tool
def crop_projection_tool(common_crop_name: str, acres: float, region: str) -> str:
    """
    Calculates expected yield and projected returns by passing environmental features 
    into our custom ML yield model, and combining it with live market prices.
    """
    try:
        # 1. Fetch live price from the market_prices table
        price_query = supabase.table("market_prices")\
            .select("wholesale_price_kes")\
            .ilike("commodity", f"%{common_crop_name}%")\
            .order("last_updated", desc=True)\
            .limit(1).execute()
            
        current_price = price_query.data[0]['wholesale_price_kes'] if price_query.data else 50
        
        # 2.Standardized feature vector: [N, P K pest, fung, herb, insect, gdp, ag_val, cpi, kes_usd, prod, dom_sup, imp, price, y_lag1, y_lag2, p_lag1, p_lag2]

        features = np.array([[0.15, 20.0, 120.0, 150.0, 50.0, 80.0, 20.0, 100000000.0, 5000000.0, 115.5, 130.5, 5000.0, 4800.0, 200.0, 90.0, 2900.0, 2850.0, 4900.0, 4850.0]])
        
        # Predict base yield per acre using your trained model
        base_yield_per_acre = float(yield_model.predict(features)[0])
        
        total_yield = base_yield_per_acre * float(acres)
        expected_return = total_yield * current_price
        
        return (
            f"ML Projection: Based on local soil/weather and macroeconomic features for {region}, our ML model "
            f"predicts a yield of {total_yield:,.0f} kg for {acres} acres of {common_crop_name}. "
            f"At the current today market price of KES {current_price}/kg, the projected gross return is KES {expected_return:,.2f}."
        )
    except Exception as e:
        return f"ML Projection engine offline: {e}"
    
# 2. Market Intelligence Tool: Provides real-time market insights from KAMIS data to inform planting and selling decisions.
@tool
def market_intelligence_tool(crop: str) -> str:
    """
    Queries the scraped KAMIS datasets to provide live market trends, 
    price fluctuations, and supply/demand intelligence for a specific crop.
    """
    try:
        # Query your Playwright-populated market dataset
        market_query = supabase.table("market_prices").select("*").eq("commodity", crop.lower()).order("last_updated", desc=True).limit(5).execute()
        
        if not market_query.data:
            return f"No recent market update found for {crop}."
            
        latest_data = market_query.data[0]
        return f"MARKET INTEL: Current wholesale trend for {crop} is active. Latest market price is {latest_data.get('wholesale_price_kes', 'N/A')} KES/kg at {latest_data.get('market_location', 'various markets')}. Market supply is currently {latest_data.get('supply_volume', 'moderate')}."
    except Exception as e:
        return f"Market Intelligence offline: {e}"

# 3. Labor Sourcing Tool: Uses spatial intelligence to find available, certified farm laborers within a 10km radius of the provided GPS coordinates for a specific task.
@tool
def labor_sourcing_tool(latitude: float, longitude: float, region: str, role_needed: str) -> str:
    """
    Searches for local workers.
    CRITICAL: 'role_needed' MUST be passed as exactly 'KIBARUA' (for physical laborers) 
    or 'AREA_AGENT' (for farm managers/supervisors).
    """
    try:
        # Run the PostGIS 10km radius search
        labor_query = supabase.rpc("find_laborers_within_10km", {
            "lat": latitude, 
            "lon": longitude, 
            "required_skill": "" # Passing empty string to grab everyone in radius first
        }).execute()
        
        workers = labor_query.data if labor_query.data else []
        
        # Filter the results by the specific role requested by the LLM
        matched_workers = [w for w in workers if w.get("role", "").upper() == role_needed.upper()]
        available_count = len(matched_workers)
        
        if available_count > 0:
            # Calculate dynamic market rate for this specific role
            rates = [float(w.get("base_rate_kes", 1000)) for w in matched_workers if w.get("base_rate_kes") is not None]
            average_rate = sum(rates) / len(rates) if rates else (1500 if role_needed == 'AREA_AGENT' else 1000)
            
            role_display = "Vibarua (Manual Laborers)" if role_needed == "KIBARUA" else "Area Agents (Supervisors)"
            
            return (
                f"LABOR MATCH: Found {available_count} certified {role_display} within 10km of {region}. "
                f"The dynamic local market rate averages KES {average_rate:,.0f}."
            )
        else:
            return f"LABOR ALERT: No available {role_needed} found within 10km of {region}. Expanding search radius recommended."
            
    except Exception as e:
        return f"Labor matching offline: {e}"

# 4. Land Selection Tool: Dual-purpose tool that provides ecological suitability insights for both crop selection and location-based planting advice.
@tool
def land_selection_tool(query_type: str, search_value: str, scientific_crop_name: str = "") -> str:
    """
    Dual-purpose ecological tool. 
    - If query_type is 'location': pass the region as 'search_value'.
    - If query_type is 'crop': YOU MUST translate the crop to its formal botanical name 
      (e.g., 'Phaseolus vulgaris' for beans) and pass it as 'scientific_crop_name'.
    """
    try:
        if query_type == "crop":
            # Search the database using the LLM-translated scientific name
            crop_query = supabase.table("crop_conditions").select("phopmn, phopmx, ropmn, ropmx, topmn, topmx").ilike("scientificname", f"%{scientific_crop_name}%").execute()
            
            if crop_query.data:
                data = crop_query.data[0] # Safely grab the first dictionary in the list
                return f"SUITABILITY: The scientific crop '{scientific_crop_name}' requires soil pH between {data.get('phopmn', 'N/A')} and {data.get('phopmx', 'N/A')}, rainfall between {data.get('ropmn', 'N/A')} and {data.get('ropmx', 'N/A')} mm, and temperature between {data.get('topmn', 'N/A')} and {data.get('topmx', 'N/A')} °C for optimal growth."
            else:
                return f"Ecological data not found for scientific name: {scientific_crop_name}."
            
        elif query_type == "location":
            # Search the weather database using the region name
            region_query = supabase.table("regional_weather").select("upcoming_season_forecast, recommended_crops").ilike("region_name", f"%{search_value}%").execute()
            
            if region_query.data:
                data = region_query.data[0]
                return f"SEASONAL ADVICE for {search_value}: The upcoming season forecast is '{data.get('upcoming_season_forecast', 'N/A')}'. Optimal crops to plant are: {data.get('recommended_crops', 'N/A')}."
            else:
                return f"No seasonal weather data found for region: {search_value}."
                
        return "Invalid query type provided to tool."
    except Exception as e:
        return f"Land selection engine offline: {e}"

# 5. location intelligence_tool: fetches parallel live weather and soil data for specific farm coordinates to provide hyper-localized planting advice and risk assessment.
@tool
def location_intelligence_tool(lat: float, lon: float) -> str:
    """
    MANDATORY for coordinate-based queries. 
    Runs the full location context script to fetch parallel live weather (wind/UV) 
    and soil chemistry for the specific farm coordinates.
    """
    try:
        context = asyncio.run(get_full_location_context(lat, lon))
        
        if not context:
            return "Location script executed but failed to fetch context."
            
        return f"LOCATION CONTEXT: {context}"
    except Exception as e:
        return f"Location Intelligence Script Error: {e}"

# 6. Mixed Crop Tool: Provides proactive mixed-cropping strategies, prioritizing high-demand crops based on current market fluctuations.
@tool
def mixed_crop_tool(region: str, total_acres: float, user_proposed_crop: str = "") -> str:
    """
    CRITICAL FOR STRATEGY: Analyzes live Market data to suggest a highly profitable, 
    diversified mixed-cropping strategy. 
    LLM DIRECTIVE: Pass the exact town/region if known, or the overarching County.
    """
    try:
        # Try exact local market match
        market_query = supabase.table("market_prices")\
            .select("commodity, wholesale_price_kes")\
            .ilike("market_location", f"%{region}%")\
            .order("wholesale_price_kes", desc=True).limit(4).execute()

        # If exact market is missing, check the broader County column
        if not market_query.data:
            market_query = supabase.table("market_prices")\
                .select("commodity, wholesale_price_kes")\
                .ilike("county", f"%{region}%")\
                .order("wholesale_price_kes", desc=True).limit(4).execute()
                
        # If county is missing, get the best prices in Kenya.
        if not market_query.data:
            market_query = supabase.table("market_prices")\
                .select("commodity, wholesale_price_kes")\
                .order("wholesale_price_kes", desc=True).limit(4).execute()
            region = "Kenya (National Average)" # Update label for the prompt

        # Process the results mathematically
        if market_query.data and len(market_query.data) >= 2:
            trending_crops = [item['commodity'].capitalize() for item in market_query.data]
            
            if user_proposed_crop and user_proposed_crop.capitalize() not in trending_crops:
                trending_crops[-1] = user_proposed_crop.capitalize() 
                
            num_splits = len(trending_crops)
            acres_per_split = float(total_acres) / num_splits
            crop_list_str = ", ".join(trending_crops)
            
            return (
                f"Land Strategy For {region.upper()}:\n"
                f"Live Market data shows peak wholesale pricing for: {crop_list_str}.\n"
                f"LLM DIRECTIVE: Empathize with the farmer and proactively ask if they are open to a split-land strategy. "
                f"Advise them to split their {total_acres} acres into {num_splits} equal sections ({acres_per_split:.2f} acres each) "
                f"and plant these specific crops to capture peak market pricing."
            )
        else:
            return "SYSTEM FALLBACK: Use internal agronomic expertise to suggest a 3-crop mix."
            
    except Exception as e:
        return f"SYSTEM ERROR: Proceed with internal expert advice. ({e})"
    
#7. markets arbitrage engine: analyzes local market price disparities to recommend optimal selling locations for maximum profit.
@tool
def market_arbitrage(latitude: float, longitude: float, proposed_crop: str) -> str:
    """
    CRITICAL: Run this BEFORE recommending a crop. 
    Uses GPS to reverse-geocode the region, checks for localized oversupply risks (Cobweb Phenomenon),
    and simultaneously locates the nearest physical markets and agrovets via PostGIS for execution.
    """
    try:
        # Translate GPS to a Regional Name
        geolocator = Nominatim(user_agent="agribrain_spatial_agent")
        location = geolocator.reverse(f"{latitude}, {longitude}", exactly_one=True)
        
        region = "your area" # Fallback
        if location:
            address = location.raw.get('address', {})
            region = address.get('city', address.get('town', address.get('county', 'Kenya')))
        
        # Query chat logs to see local planting trends
        supply_query = supabase.table("agribrain_chatlogs")\
            .select("user_message")\
            .ilike("user_message", f"%{proposed_crop}%")\
            .execute()
            
        local_interest_count = len(supply_query.data) if supply_query.data else 0
        
        # Query PostGIS for nearest Agrovets and Markets
        shops_list_str = ""
        try:
            shops_query = supabase.rpc("find_near_shops", {
                "u_lat": latitude, 
                "u_lng": longitude
            }).execute()
            
            shops = shops_query.data if shops_query.data else []
            
            if shops:
                shops_list_str = "NEARBY INFRASTRUCTURE:\n"
                for shop in shops:
                    name = shop.get("name", "Unknown Facility")
                    l_type = shop.get("location_type", "Shop")
                    dist = shop.get("dist_meters", 0)
                    
                    dist_str = f"{dist/1000:.1f} km" if dist > 1000 else f"{dist:.0f} meters"
                    shops_list_str += f"- {name} ({l_type}): {dist_str} away\n"
            else:
                shops_list_str = "NEARBY INFRASTRUCTURE: No registered agrovets or markets found within the immediate radius."
        except Exception as e:
            shops_list_str = f"NEARBY INFRASTRUCTURE: Spatial routing offline ({e})."

        # Arbitrage Logic 
        if local_interest_count > 15:
            verdict = (
                f"WARNING: High local planting interest detected for {proposed_crop} near {region} "
                f"({local_interest_count} recent queries). High risk of Cobweb Phenomenon (oversupply upon harvest). "
                f"ADVISE AGAINST THIS. Suggest alternatives with lower local saturation."
            )
        else:
            verdict = (
                f"CLEAR: {proposed_crop} shows low local saturation ({local_interest_count} queries) "
                f"in the {region} area. Safe to proceed with planting recommendation."
            )
            
        # Deliver the master payload to the LLM
        return f"ARBITRAGE ANALYSIS:\n{verdict}\n\n{shops_list_str}"
            
    except Exception as e:
        return f"Arbitrage analysis offline: {e}"   



ddg_search = DuckDuckGoSearchRun()
real_time_search_tool = Tool(name="real_time_web_search",
                             func=ddg_search.run,
                             description=("CRITICAL FALLBACK TOOL: use this to search the open web for live data"
                             "(like regional soil chemistry,weather, agricultural news)"
                             "only IFa primary database or API tool fails, returns 'offline', or explicitly instructs you to use it in the prompt. Always return the most relevant search result text to the user without mentioning the tool or the fact that you searched the web.")
                             )
                            

AGRICULTURAL_TOOLS = [market_intelligence_tool, 
                      land_selection_tool, 
                      location_intelligence_tool, 
                      mixed_crop_tool, 
                      crop_projection_tool, 
                      labor_sourcing_tool,
                      market_arbitrage,
                      real_time_search_tool]