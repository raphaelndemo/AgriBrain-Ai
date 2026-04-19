import os
import requests
import pandas as pd
import time
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("Missing Supabase keys.")
supabase: Client = create_client(url, key)

def fetch_with_retries(target_url, max_retries=3, delay_seconds=5):
    for attempt in range(max_retries):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(target_url, headers=headers, timeout=15)
            response.raise_for_status() 
            return response
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
            else:
                return None

def update_market_prices():
    print("Initiating Daily Market Price Sync")
    
    api_url = "https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-kenya"
    temp_file = "temp_wfp_prices.csv"
    
    api_response = fetch_with_retries(api_url)
    if not api_response: return

    data = api_response.json()
    csv_url = None
    
    if data.get('success'):
        for resource in data['result']['resources']:
            if resource.get('format', '').upper() == 'CSV':
                csv_url = resource.get('url')
                break

    if not csv_url:
        print("ERROR: Could not find the CSV link in the API.")
        return

    csv_response = fetch_with_retries(csv_url)
    if not csv_response: return
         
    try:
        with open(temp_file, "wb") as f:
            f.write(csv_response.content)
        df = pd.read_csv(temp_file, low_memory=False)
    except Exception as e:
        print(f"ERROR reading CSV: {e}")
        return
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    print("Filtering data..")
    df_clean = df[['date', 'market', 'commodity', 'pricetype', 'price']].dropna()
    df_clean['date'] = pd.to_datetime(df_clean['date'], errors='coerce')
    df_latest = df_clean.dropna(subset=['date']).sort_values('date').tail(200)
    
    records = []
    for _, row in df_latest.iterrows():
        records.append({
            "crop_name": str(row['commodity']).lower().strip(),
            "market_location": str(row['market']).strip(),
            "retail_price_kes": float(row['price']) if row['pricetype'] == 'Retail' else None,
            "wholesale_price_kes": float(row['price']) if row['pricetype'] == 'Wholesale' else None,
            "price_date": row['date'].strftime('%Y-%m-%d') # Correctly tracks the date!
        })
        
    print("Pushing to table in Supabase...")
    try:
        supabase.table('kenyan_markets').upsert(records).execute()
        print("Database Updated Successfully")
    except Exception as e:
        print(f"ERROR pushing to Supabase: {e}")

if __name__ == "__main__":
    update_market_prices()
