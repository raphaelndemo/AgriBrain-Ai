import os
import joblib

# Isolate the exact path within the  container 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YIELD_MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "yield_predictor.pkl")
MARKET_MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "market_forecaster.pkl")

def load_ml_model(path: str, model_name: str):
    """Deserializes pre-trained Scikit-Learn/XGBoost structures into RAM."""
    try:
        return joblib.load(path)
    except Exception as e:
        print(f"MLOps Error: Asset {model_name} failed to load: {e}")
        return None

yield_model = load_ml_model(YIELD_MODEL_PATH, "Yield Predictor")
market_model = load_ml_model(MARKET_MODEL_PATH, "Market Forecaster")