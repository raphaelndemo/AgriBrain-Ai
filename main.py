from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="AgriBrain API",
    description="Crop yield prediction backend for AgriBrain",
    version="1.0.0"
)


class FarmInput(BaseModel):
    rainfall_mm: float = Field(..., ge=0, description="Rainfall in millimeters")
    temperature_c: float = Field(..., ge=-20, le=60, description="Temperature in degrees Celsius")
    soil_moisture: float = Field(..., ge=0, le=1, description="Soil moisture from 0 to 1")


@app.get("/")
def root():
    return {
        "message": "AgriBrain API is running 🌱",
        "status": "success"
    }


@app.post("/predict")
def predict(data: FarmInput):
    # Simple demo formula for now
    prediction = (
        (data.rainfall_mm * 0.3) +
        (data.temperature_c * 0.5) +
        (data.soil_moisture * 10)
    )

    if prediction >= 50:
        advice = "High yield potential detected. Maize may perform well under these conditions 🌽"
    elif prediction >= 30:
        advice = "Moderate yield expected. Monitor rainfall and soil conditions closely 🌿"
    else:
        advice = "Lower yield potential detected. Review planting conditions before planting ⚠️"

    return {
        "predicted_yield": round(prediction, 2),
        "advice": advice,
        "input_received": {
            "rainfall_mm": data.rainfall_mm,
            "temperature_c": data.temperature_c,
            "soil_moisture": data.soil_moisture
        }
    }