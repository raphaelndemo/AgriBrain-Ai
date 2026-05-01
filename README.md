# AgriBrain-Ai

**AgriBrain** is an end-to-end agritech recommendation engine that helps Kenyan farmers optimize crop selection by combining real-time soil, weather, yield, and market data.

It actively combats the **"Cobweb Phenomenon"** — the cycle of oversupply and price crashes caused by reliance on past experience and historical prices.

The platform helps reduce the aspect of guesswork in decision making on what to crop and offers alternative profitable crops that the farmer could plant.

>  **Live Demo:** https://your-demo-link-here.netlify.app *(Add link when deployed)*

---

##  Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Datasets](#-datasets)
- [Notebook Pipeline](#-notebook-pipeline)
- [Models & Algorithms](#-models--algorithms)
- [Key Outputs](#-key-outputs)
- [Setup & Installation](#-setup--installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Key Design Decisions](#-key-design-decisions)
- [Known Limitations](#-known-limitations)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 🌍 Overview

AgriBrain breaks the traditional cycle of guesswork in Kenyan agriculture by delivering **data-driven crop recommendations**.

It helps farmers choose high-demand, ecologically viable crops that maximize profitability while supporting national food security.

###  What the system delivers:

| Output | Description |
|--------|------------|
| **Crop Recommendations** | Top crops with predicted yield and market potential |
| **Market Signal** | Shortage / Balanced / Oversupply risk |
| **Yield Forecast** | Predicted yield (kg/ha) using ensemble models |
| **Price Forecast** | Future price trends using time-series ensembles |
| **Profitability Insight** | Estimated revenue potential |

---

## System Architecture

    Farmer Input (Location, Soil, Season, Preferences)
            │
            ▼
    ┌──────────────────────────────────────────────┐
    │ Stage 1 — Yield Prediction Engine            │
    │ Ensemble: XGBoost + Random Forest + Prophet  │
    └──────────────────────┬───────────────────────┘
                           │ Predicted Yield
                           ▼
    ┌──────────────────────────────────────────────┐
    │ Stage 2 — Market Intelligence Engine         │
    │ Supply/Demand Balance + Stock Deficit        │
    │ → Market Signal (Shortage / Oversupply)      │
    └──────────────────────┬───────────────────────┘
                           │ Enriched Crop Profiles
                           ▼
    ┌──────────────────────────────────────────────┐
    │ Stage 3 — Price Forecasting Engine           │
    │ Ensemble: XGBoost + RF + ARIMA + Prophet     │
    └──────────────────────┬───────────────────────┘
                           │ Price & Profitability
                           ▼
            Final Recommendation Output

---

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

## ⚙️ Setup & Installation

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
## Future Recommendations
- Automated location detection via mobile for hyper-local recommendations
- Integration of satellite and remote sensing data
- Labor marketplace integration
- Mixed cropping optimization
- Expansion of KAMIS dataset to cover more counties
- Advanced environmental analytics using live weather and soil sensor data

## 🛣️ Roadmap

- [ ] Integrate real-time weather & soil data  
- [ ] Add LLM-powered market analysis agent  
- [ ] Build web/mobile dashboard  
- [ ] Fertilizer & pest risk modeling  
- [ ] Deploy production API  
- [ ] Expand to more regions & crops  

---

## 📜 License

This project is for academic and research purposes.

FAOSTAT and KAMIS data usage must comply with their respective terms.
