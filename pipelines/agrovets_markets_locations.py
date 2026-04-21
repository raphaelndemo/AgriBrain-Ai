import requests
import pandas as pd
import time
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

def fetch_kenya_spatial_data_deep_scan():
    print("Booting up Overpass API for a DEEP SCAN of Kenya...")
    
    headers = {
        "User-Agent": "AgriBrain_ETL_Pipeline/2.0 (Data Science Academic Project)"
    }
    
    endpoints = [
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]
    
    # 1. THE NEW QUERY: Using 'nwr' (Nodes, Ways, Relations) to catch large markets
    # and expanding the 'shop' tags to catch specialized agrovets.
    overpass_query = """
    [out:json][timeout:120];
    area["ISO3166-1"="KE"][admin_level=2]->.searchArea;
    (
      nwr["amenity"="marketplace"](area.searchArea);
      nwr["amenity"="market"](area.searchArea);
      
      nwr["shop"="agronomist"](area.searchArea);
      nwr["shop"="agricultural"](area.searchArea);
      nwr["shop"="farm"](area.searchArea);
      nwr["shop"="fertilizer"](area.searchArea);
      nwr["shop"="seeds"](area.searchArea);
      nwr["shop"="pesticide"](area.searchArea);
      nwr["shop"="animal_feed"](area.searchArea);
    );
    out center;
    """
    
    data = None
    for url in endpoints:
        try:
            print(f"Attempting to connect to {url}...")
            response = requests.post(url, data={'data': overpass_query}, headers=headers, timeout=120)
            response.raise_for_status()
            data = response.json()
            print("Successfully connected to Overpass API!")
            break 
        except Exception as e:
            print(f"Failed on {url}. Error: {e}")
            time.sleep(2) 

    if not data:
        print("ERROR: Failed to reach ALL Overpass API endpoints.")
        return None

    elements = data.get('elements', [])
    print(f"Retrieved {len(elements)} raw spatial points/areas.")
    
    records = []
    for el in elements:
        tags = el.get('tags', {})
        
        # 2. Extract logic updated for nwr center points
        if tags.get('amenity') in ['marketplace', 'market']:
            loc_type = 'Market'
        else:
            loc_type = 'Agrovet'
            
        name = tags.get('name', f"Unnamed {loc_type}")
        
        # If it's a Node, it has lat/lon. If it's a Way/Relation, it has a 'center' dictionary.
        if el.get('type') == 'node':
            lat = el.get('lat')
            lon = el.get('lon')
        else:
            lat = el.get('center', {}).get('lat')
            lon = el.get('center', {}).get('lon')
            
        records.append({
            "location_name": name,
            "location_type": loc_type,
            "latitude": lat,
            "longitude": lon
        })
        
    df = pd.DataFrame(records)
    df = df.dropna(subset=['latitude', 'longitude'])
    df = df.drop_duplicates(subset=['latitude', 'longitude'])
    
    print(f"Cleaned down to {len(df)} verified locations.")
    print("Pushing into Supabase 'agrovets_markets' table...")
    
    records_dict = df.to_dict(orient='records')
    chunk_size = 500
    
    try:
        for i in range(0, len(records_dict), chunk_size):
            chunk = records_dict[i:i + chunk_size]
            supabase.table('agrovets_markets').upsert(chunk).execute()
            print(f"Pushed chunk {i} to {i + len(chunk)}...")
            
        print("All extended Agrovets and Markets successfully pushed to database!")
    except Exception as e:
        print(f"ERROR pushing spatial data to Supabase: {e}")

    return df

if __name__ == "__main__":
    fetch_kenya_spatial_data_deep_scan()