import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("Missing Supabase keys.")
supabase: Client = create_client(url, key)

def process_and_upload_ecocrop():
    print("Initializing Pipeline")
    csv_file = "EcoCrop_DB.csv"
    
    if not os.path.exists(csv_file):
        print(f"ERROR: Could not find {csv_file}")
        return
        
    df = pd.read_csv(csv_file, low_memory=False, encoding='latin1')
    print(f"Loaded {len(df)} raw rows.")

    # 1.FEATURE SELECTION
    cols_to_drop = ['AUTH', 'SYNO', 'LISPA', 'PHOTO', 'INTRI', 'PROSY', 'ABISUS', 'ABITOL', 'CLIZ', 'CAT']
    df = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
    print(f"Dropped {len(cols_to_drop)} irrelevant columns. {len(df.columns)} columns remain.")

    # Lowercase headers to match database
    df.columns = [str(col).lower().strip() for col in df.columns]

    # 2.DATA cleaning
    print("Imputing missing values (Medians for numbers, Modes for text)...")
    
    # Clean nulls 
    df = df.replace(r'^\s*$|^null$|^NaN$', np.nan, regex=True)

    # Fill numerical missing values with Median
    num_cols = df.select_dtypes(include=['float64', 'int64']).columns
    for col in num_cols:
        df[col] = df[col].fillna(df[col].median())

    # Fill categorical text missing values with the Mode
    cat_cols = df.select_dtypes(include=['object']).columns
    for col in cat_cols:
        mode_val = df[col].mode()
        if not mode_val.empty:
            df[col] = df[col].fillna(mode_val)
        else:
            df[col] = df[col].fillna("unknown")

    #Database prep
    raw_records = df.to_dict(orient="records")
    clean_records = [
        {k: (None if pd.isna(v) else v) for k, v in row.items()} 
        for row in raw_records
    ]
    
    # Push to Supabase
    print(f"Pushing {len(clean_records)}cleaned records to Supabase--")
    batch_size = 500
    for i in range(0, len(clean_records), batch_size):
        batch = clean_records[i:i + batch_size]
        try:
            supabase.table('crop_conditions').upsert(batch).execute()
            print(f"Batch {i//batch_size + 1} pushed successfully.")
        except Exception as e:
            print(f"Error on batch {i//batch_size + 1}: {e}")
            
    print("Complete")

if __name__ == "__main__":
    process_and_upload_ecocrop()
