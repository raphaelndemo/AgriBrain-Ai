import os
import joblib
from google.cloud import storage


# CONFIGURATION
BUCKET_NAME = "agribrain-models"
LOCAL_MODEL_DIR = "ml_models"

YIELD_MODEL_FILENAME = "yield_predictor.pkl"
MARKET_MODEL_FILENAME = "market_forecaster.pkl"

YIELD_MODEL_PATH = os.path.join(LOCAL_MODEL_DIR, YIELD_MODEL_FILENAME)
MARKET_MODEL_PATH = os.path.join(LOCAL_MODEL_DIR, MARKET_MODEL_FILENAME)

# ASSET RETRIEVAL PROTOCOL
def download_models_from_bucket():
    """
    The pipeline securely streams ML models from Google Cloud Storage 
    into the local container storage prior to application initialization.
    """
    os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
    
    # Skip download if the models already exist 
    if os.path.exists(YIELD_MODEL_PATH) and os.path.exists(MARKET_MODEL_PATH):
        print("ML models already exist locally. Skipping download.")
        return

    try:
        print("Initializing secure connection to Google Cloud Storage")
        # The client automatically inherits IAM permissions from Cloud Run
        client = storage.Client() 
        bucket = client.bucket(BUCKET_NAME)
        
        # Download Yield Predictor
        yield_blob = bucket.blob(YIELD_MODEL_FILENAME)
        yield_blob.download_to_filename(YIELD_MODEL_PATH)
        print(f"Successfully downloaded {YIELD_MODEL_FILENAME}")
        
        # Download Market Forecaster
        market_blob = bucket.blob(MARKET_MODEL_FILENAME)
        market_blob.download_to_filename(MARKET_MODEL_PATH)
        print(f"Successfully downloaded {MARKET_MODEL_FILENAME}")
        
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to retrieve models from cloud storage: {e}")

# MEMORY ALLOCATION & LOADING
def load_ml_model(path):
    """The system deserializes the model weights into active memory."""
    try:
        return joblib.load(path)
    except Exception as e:
        print(f" Warning: Failed to load ML asset at {path}. Error: {e}")
        return None

# 1. Execute the download protocol
download_models_from_bucket()

# 2. Load the downloaded models into global variables for the LangChain tools to use
print("Loading models into active memory")
yield_model = load_ml_model(YIELD_MODEL_PATH)
market_model = load_ml_model(MARKET_MODEL_PATH)
print("Machine Learning Engine Ready.")