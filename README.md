# AgriBrain-Ai

**AgriBrain-AI** is an advanced, multimodal artificial intelligence assistant engineered specifically for Kenyan farmers. By combining Large Language Models (Gemini 2.5 Flash), Machine Learning yield projections, and real-time PostGIS spatial data, it provides hyper-local agricultural intelligence to optimize yields, prevent market over-saturation (the "Cobweb Phenomenon"), and route local labor.

>  **Live Demo:** https://agribrain-ai-1022818522174.africa-south1.run.app/ 

---

##  Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-feautures)
- [Achitectural Layers](#-achitectural-layers)
- [Datasets](#-datasets)
- [Notebook Pipeline](#-notebook-pipeline)
- [Models & Algorithms](#-models--algorithms)
- [Key Outputs](#-key-outputs)
- [Setup & Installation](#-setup--installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Key Design Decisions](#-key-design-decisions)
- [License](#-license)

---

##  Overview

AgriBrain breaks the traditional cycle of guesswork in Kenyan agriculture by delivering **data-driven crop recommendations**.

It helps farmers choose high-demand, ecologically viable crops that maximize profitability while supporting national food security.

### Key Features
Multimodal AI Diagnostics: Farmers can upload images of diseased crops via web or WhatsApp. The system dynamically compresses and analyzes the images using Gemini 2.5 Flash to provide instant agronomic advice.
PostGIS Geospatial Routing: Utilizes advanced SQL spatial queries to instantly connect farmers with agricultural laborers (vibarua / area agents) and agrovets within a 10km radius of their precise GPS coordinates.
Predictive ML Yield Engine: A Random Forest Regressor trained on 19 complex macroeconomic and agrochemical features (including CPI, exchange rates, and lagged yields) to calculate precise harvest projections.
Cascading Market Arbitrage: Queries live KAMIS market databases to calculate local crop saturation. Features a self-healing geographical fallback (Town ➡️ County ➡️ National) to ensure farmers always receive actionable pricing data.
Privacy-First Telemetry: Automated tracking of AI interactions with programmatic phone number masking (e.g., 0712***215) to strictly adhere to Kenyan Data Protection Act (KDPA) and GDPR regulations.

---

## Architectural Layers
AgriBrain-AI is built on a highly resilient, loosely coupled Microservice Architecture:
The Interface Layer (Microservices):
Web UI (app.py): A standalone Chainlit application featuring secure phone-based authentication and text-to-coordinate geocoding (via geopy).
Meta Webhook (whatsapp_webhook.py): An isolated FastAPI node that securely ingests Meta Graph API payloads, processes native GPS pins, and downloads binary image bytes.
The Intelligence Layer (router.py): The LangChain AgentExecutor. It holds the conversational memory, standardizes multimodal inputs, and orchestrates the suite of agricultural tools.
The Data Layer (Supabase/PostgreSQL): A strictly normalized relational database. Separates permanent user state (user_profiles with Lat/Lon) from time-series event logs (agribrain_chatlogs), while utilizing PostGIS extensions for spatial mapping (worker_profiles).
    

##  Datasets

| Dataset | Source | Type | Role |
|--------|--------|------|------|
| Yield Data | FAOSTAT | Yearly | Historical crop yields (kg/ha) |
| Food Balance | FAOSTAT | Yearly | Production, imports, exports |
| Market Prices | KAMIS | Daily | Wholesale & retail prices |
| Macro Indicators | FAOSTAT | Yearly | Economic/agricultural indicators |

>  Raw files are stored in `csvfiles/`  
> Processed outputs are saved as clean DataFrames

---

##  Notebook Pipeline

| # | Notebook | Description |
|---|----------|------------|
| 1 | `datapreparation.ipynb` | Data cleaning, feature engineering, EDA |
| 2 | `yield_modeling.ipynb` | Yield prediction ensemble |
| 3 | `price_ensemble_model.ipynb` | Price forecasting ensemble |
| 4 | `full_integration.ipynb` | End-to-end pipeline *(planned)* |

---

###  Yield Prediction
- Ensemble: **XGBoost + Random Forest + Prophet**
- Goal: Predict crop yield (kg/ha)

###  Price Forecasting
- Ensemble: **XGBoost + Random Forest + ARIMA + Prophet**
- Goal: Forecast future market prices
- Metrics: MAE, RMSE

###  Market Intelligence
- **Supply-Demand Balance:**
  (Production + Imports) - (Food + Feed + Exports + Losses)

- **Market Signal:**
  - Shortage
  - Balanced
  - Oversupply

---

## Key Outputs

Example system output:

    {
      "crop": "Maize",
      "predicted_yield_kg_per_ha": 4520.3,
      "market_signal": "oversupply",
      "predicted_price": 45.8,
      "estimated_revenue": 207000,
      "risk_level": "High",
      "recommendation_score": 0.87
    }

---

##  Models Results and Intepratation
### Yield Prediction results
<img width="251" height="220" alt="Yield Prediction Results" src="https://github.com/user-attachments/assets/a7dbee13-c7b3-4309-816e-54d6825cd323" />

The results predict how off our yield predictions are from the actual yield. Therefore, we will consider the moel that has the least value in its MAE and RSME. From the model results, we are checked how off our model is in terms of yield prediction. The stacked model was the best since it has the least errors in yield prediction compared to the other models.

### Price prediction results
<img width="312" height="218" alt="price prediction results" src="https://github.com/user-attachments/assets/93137ab1-9a46-463b-9216-968566d9360e" />

The stacked model is among those with the best overall balance of MAE and RMSE making it the most reliable model for market price prediction across Kenya's top commodities.

##  Setup & Installation

###  Prerequisites
- Python 3.9+
- Jupyter Notebook

###  Install Dependencies

    pip install pandas numpy scikit-learn xgboost prophet statsmodels matplotlib seaborn joblib

---

##  Usage

    import joblib
    import pandas as pd

    # Load models
    yield_model = joblib.load("yield_ensemble_model.pkl")
    price_model = joblib.load("price_ensemble_model.pkl")

---

##  Project Structure

    AgriBrain/
    ├── csvfiles/                    # Raw datasets (FAOSTAT & KAMIS)
    ├── datapreparation.ipynb        # Data prep & EDA
    ├── yield_ensemble_model.pkl     # Yield model
    ├── price_ensemble_model.pkl     # Price model
    ├── README.md
    └── requirements.txt

---

##  Key Design Decisions

- **Ensemble Modeling:** Combines ML + time-series models for robustness  
- **Market Balance Metric:** Captures real supply-demand dynamics  
- **Kenya-Focused:** Built specifically for local crops & markets  
- **Modular Design:** Easy integration of weather/soil APIs  

---
## Real World Applications
- AgriBrain supports multiple use cases:
- crop planning and selection
- land investment analysis
- disease detection through images
- market optimization strategies
- Each workflow is context-aware and data-driven.

##  Known Limitations
- FAOSTAT data is yearly, limiting real-time responsiveness
- ARIMA and SARIMA do not handle multivariate inputs well
- Price predictions limited to commodities covered by KAMIS
- System does not yet account for pest and disease outbreaks
- Model accuracy depends heavily on data quality and completeness

---

## Roadmap

- [ ] Integrate real-time weather & soil data  
- [ ] Add LLM-powered market analysis agent  
- [ ] Build web/mobile dashboard  
- [ ] Fertilizer & pest risk modeling  
- [ ] Deploy production API  
- [ ] Expand to more regions & crops  

---

## License

This project is for academic and research purposes.

FAOSTAT and KAMIS data usage must comply with their respective terms.
