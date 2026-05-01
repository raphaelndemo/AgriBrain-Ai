# AgriBrain-Ai
AI-powered agricultural intelligence platform built for smallholder farmers in Kenya.
# 🌾 AgriBrain

**AgriBrain** is an end-to-end agritech recommendation engine that helps Kenyan farmers optimize crop selection by combining real-time soil, weather, yield, and market data.

It actively combats the **"Cobweb Phenomenon"** — the cycle of oversupply and price crashes caused by reliance on past experience and historical prices.

> 🔗 **Live Demo:** https://your-demo-link-here.netlify.app *(Add link when deployed)*

---

## 📌 Table of Contents

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

### ✅ What the system delivers:

| Output | Description |
|--------|------------|
| **Crop Recommendations** | Top crops with predicted yield and market potential |
| **Market Signal** | Shortage / Balanced / Oversupply risk |
| **Yield Forecast** | Predicted yield (kg/ha) using ensemble models |
| **Price Forecast** | Future price trends using time-series ensembles |
| **Profitability Insight** | Estimated revenue potential |

---

## 🏗️ System Architecture

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

## 📊 Datasets

| Dataset | Source | Type | Role |
|--------|--------|------|------|
| Yield Data | FAOSTAT | Yearly | Historical crop yields (kg/ha) |
| Food Balance | FAOSTAT | Yearly | Production, imports, exports |
| Market Prices | KAMIS | Daily | Wholesale & retail prices |
| Macro Indicators | FAOSTAT | Yearly | Economic/agricultural indicators |

> 📁 Raw files are stored in `csvfiles/`  
> 📦 Processed outputs are saved as clean DataFrames

---

## 📓 Notebook Pipeline

| # | Notebook | Description |
|---|----------|------------|
| 1 | `datapreparation.ipynb` | Data cleaning, feature engineering, EDA |
| 2 | `yield_modeling.ipynb` | Yield prediction ensemble |
| 3 | `price_ensemble_model.ipynb` | Price forecasting ensemble |
| 4 | `full_integration.ipynb` | End-to-end pipeline *(planned)* |

---

## 🤖 Models & Algorithms

### 🌱 Yield Prediction
- Ensemble: **XGBoost + Random Forest + Prophet**
- Goal: Predict crop yield (kg/ha)

### 💰 Price Forecasting
- Ensemble: **XGBoost + Random Forest + ARIMA + Prophet**
- Goal: Forecast future market prices
- Metrics: MAE, RMSE

### 📈 Market Intelligence
- **Supply-Demand Balance:**
  (Production + Imports) - (Food + Feed + Exports + Losses)

- **Market Signal:**
  - Shortage
  - Balanced
  - Oversupply

---

## 📤 Key Outputs

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

## ⚙️ Setup & Installation

### ✅ Prerequisites
- Python 3.9+
- Jupyter Notebook

### 📦 Install Dependencies

    pip install pandas numpy scikit-learn xgboost prophet statsmodels matplotlib seaborn joblib

---

## 🚀 Usage

    import joblib
    import pandas as pd

    # Load models
    yield_model = joblib.load("yield_ensemble_model.pkl")
    price_model = joblib.load("price_ensemble_model.pkl")

---

## 📁 Project Structure

    AgriBrain/
    ├── csvfiles/                    # Raw datasets (FAOSTAT & KAMIS)
    ├── datapreparation.ipynb        # Data prep & EDA
    ├── yield_ensemble_model.pkl     # Yield model
    ├── price_ensemble_model.pkl     # Price model
    ├── README.md
    └── requirements.txt

---

## 🧠 Key Design Decisions

- **Ensemble Modeling:** Combines ML + time-series models for robustness  
- **Market Balance Metric:** Captures real supply-demand dynamics  
- **Kenya-Focused:** Built specifically for local crops & markets  
- **Modular Design:** Easy integration of weather/soil APIs  

---

## ⚠️ Known Limitations

- Uses yearly FAOSTAT data (low temporal resolution)  
- No real-time soil or weather data yet  
- Price models require frequent retraining  
- Limited crop coverage  

---

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
