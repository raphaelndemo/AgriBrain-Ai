import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. SECURE CREDENTIAL LOADING  "No Hardcoding" Shield
load_dotenv()

# We pull the keys  using os.getenv()
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY")

# Fail-safe Stopping the script instantly if the keys are missing
if not url or not key:
    raise ValueError(" Missing Supabase keys. Please ensure your .env file is set up correctly with SUPABASE_URL and SUPABASE_ANON_KEY.")

# Initialize the secure database connection
supabase: Client = create_client(url, key)

# 2. DATA EXTRACTION
def process_and_upload_ecocrop(csv_path="EcoCrop_DB.csv"):
    """Reads the raw FAO CSV, cleans it, and pushes it to Supabase."""
    print(f"Initializing EcoCrop ETL Pipeline...")
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        print(f" Loaded {len(df)} raw rows from {csv_path}")
    except FileNotFoundError:
        print(f"ERROR: Cannot find '{csv_path}'. Please ensure the downloaded file is in this folder.")
        return

 
    # 3. DATA CLEANING & TRANSFORMATION 
    
    print(" Cleaning data and aligning with database schema...")
    
    # Map the raw CSV columns to the exact names of our Supabase SQL columns
    df_clean = pd.DataFrame({
        'crop_name': df['COMNAME'].astype(str).str.lower().str.strip(),
        'min_temp': df['TMIN'],
        'max_temp': df['TMAX'],
        'min_rainfall': df['RMIN'],
        'max_rainfall': df['RMAX'],
        'min_ph': df['PHMIN'],
        'max_ph': df['PHMAX']
    })

    # Drop any junk data
    df_clean = df_clean.dropna(subset=['crop_name', 'min_temp', 'max_temp', 'min_rainfall'])
    
    # Remove duplicate crops 
    df_clean = df_clean.drop_duplicates(subset=['crop_name'])

    # Convert the cleaned Pandas DataFrame into a list of dictionaries for Supabase
    records = df_clean.to_dict('records')
    print(f"data cleaned: {len(records)} viable crops identified.")

    
    # 4.DATABASE LOADING 
    print("Pushing data to Supabase 'eco_crop_rules' table...")
    
    # We upload in batches of 100 to prevent overwhelming the API connection
    batch_size = 100
    successful_batches = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        try:
            # The actual API call to insert the data securely
            supabase.table('eco_crop_rules').insert(batch).execute()
            successful_batches += 1
            print(f"      -> Successfully uploaded batch {successful_batches}...")
        except Exception as e:
            print(f" Error on batch {successful_batches + 1}: {e}")

    print("Complete.")

if __name__ == "__main__":
    # Run the function when the script is executed
    process_and_upload_ecocrop()