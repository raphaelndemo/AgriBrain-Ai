import os
import requests
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
import time

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

KENYA_COUNTIES = [
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo Marakwet", 
    "Embu", "Garissa", "Homa Bay", "Isiolo", "Kajiado", "Kakamega", 
    "Kericho", "Kiambu", "Kilifi", "Kirinyaga", "Kisii", "Kisumu", 
    "Kitui", "Kwale", "Laikipia", "Lamu", "Machakos", "Makueni", "Mandera", 
    "Marsabit", "Meru", "Migori", "Mombasa", "Murang'a", "Nairobi", "Nakuru", 
    "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri", "Samburu", "Siaya", 
    "Taita Taveta", "Tana River", "Tharaka Nithi", "Trans Nzoia", "Turkana",
    "Uasin Gishu", "Vihiga", "Wajir", "West Pokot"
]
def get_counties_locations_from_overpass(county):
    print(f"Starting map scan for markets and agrovets in {county}")
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Overpass query to find markets and agrovets in the specified county
    query = f"""
    [out:json][timeout:120];
    area["name"="{county}"]["admin_level"="4"]->.searchArea;
    (
      nwr["shop"~"agricultural|seeds|fertilizer|pesticide|agronomist|farm|animal_feed"](area.searchArea);
      nwr["amenity"~"market|marketplace|soko"](area.searchArea);
      nwr["shop"~"agronomist|agricultural|farm|fertilizer|seeds|pesticide|animal_feed|hardware|agrovet|farm_supplies"](area.searchArea); 
    );
    out center;
    """
    
    headers = {
        "User-Agent": "AgriBrain_Pipeline (Data Science Academic Project, contact:agribrain@moringaschool.com)",
        "Accept-charset": "utf-8"
    }

    
    #Sending the request to Overpass
    try:
        response = requests.post(overpass_url, data={'data': query}, headers=headers)
        response.raise_for_status() # Check for errors
        data = response.json()

        records = []
        for element in data.get('elements', []):
            lat = element.get('lat') or element.get('center', {}).get('lat')
            lon = element.get('lon') or element.get('center', {}).get('lon')
            tags = element.get('tags', {})

            if lat and lon:
                records.append({
                    "location_name": tags.get('name', 'Unknown Location'),
                    "location_type": 'market' if tags.get('amenity') in ['marketplace', 'soko', 'market'] else 'agrovet',
                    "latitude": lat,
                    "longitude": lon,
                    # postGIS format:
                    "geo_location": f"POINT({lon} {lat})"
                })
        return records
    except Exception as e:
        print(f"Failed to connect to Overpass for {county}. Error: {e}")
        return []
    except Exception as e:
        print(f"Failed to connect to Overpass. Error: {e}")
        return

    # clean the data
def locations_from_overpass():    
    all_locations = []
    for county in KENYA_COUNTIES:
        county_data = get_counties_locations_from_overpass(county)
        if county_data:
           supabase.table('agrovets_markets').upsert(county_data, on_conflict='latitude,longitude').execute() # Push to Supabase 
        all_locations.extend(county_data)
        print(f"Found {len(county_data)} locations in {county}.")
        time.sleep(10)  # Sleep for 10 second between requests to avoid hitting rate limits
    

    print("Completed fetching locations from Overpass")    

if __name__ == "__main__":
    locations_from_overpass()