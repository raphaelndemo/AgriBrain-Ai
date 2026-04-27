# backend_scripts/models.py
import os
import joblib
import numpy as np

# Global variables to hold the models in memory
_yield_model = None
_market_model = None

def _load_models():
    """Loads models into memory only once."""
    global _yield_model, _market_model
    
    if _yield_model is None or _market_model is None:
        print("Loading ML Models into memory...")
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            yield_path = os.path.join(BASE_DIR, "ml_models", "yield_predictor.pkl")
            market_path = os.path.join(BASE_DIR, "ml_models", "Market_price_predictor.pkl")
            
            _yield_model = joblib.load(yield_path)
            _market_model = joblib.load(market_path)
            print("✅ Models loaded successfully!")
        except Exception as e:
            print(f"⚠️ Warning: Could not load ML models. Error: {e}")

def get_yield_prediction(features_list) -> float:
    """Instantly runs the yield prediction."""
    _load_models()
    if _yield_model:
        # Convert list to a 2D numpy array for the model
        features = np.array([features_list])
        return float(_yield_model.predict(features))
    return 20.0 # Fallback if model is missing

def get_market_prediction(features_list) -> float:
    """Instantly runs the market price prediction."""
    _load_models()
    if _market_model:
        features = np.array([features_list])
        return float(_market_model.predict(features))
    return 0.0 # Fallback