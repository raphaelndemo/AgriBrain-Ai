from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="AgriBrain API", version="1.0.0")


class FarmInput(BaseModel):
    rainfall_mm: float = Field(..., ge=0)
    temperature_c: float = Field(..., ge=-20, le=60)
    soil_moisture: float = Field(..., ge=0, le=1)


@app.get("/")
def root():
    return {"message": "AgriBrain API is running 🌱"}


@app.post("/predict")
def predict(data: FarmInput):
    rainfall_score = min(data.rainfall_mm / 150, 1)
    temp_score = max(0, 1 - abs(data.temperature_c - 25) / 15)
    moisture_score = data.soil_moisture

    score = (rainfall_score * 0.4) + (temp_score * 0.3) + (moisture_score * 0.3)

    predicted_yield = round(0.8 + (score * 5.7), 2)

    if predicted_yield >= 5:
        advice = "Conditions look strong. Maize may perform well, but continue monitoring rainfall and soil moisture."
    elif predicted_yield >= 2.5:
        advice = "Conditions are fair. Consider monitoring water levels closely before planting."
    else:
        advice = "Conditions may be risky. It may be better to wait, improve soil moisture, or seek local field advice."

    return {
        "predicted_yield": predicted_yield,
        "advice": advice,
        "input_received": {
            "rainfall_mm": data.rainfall_mm,
            "temperature_c": data.temperature_c,
            "soil_moisture": data.soil_moisture,
        },
    }