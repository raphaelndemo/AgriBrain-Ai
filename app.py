import requests
import chainlit as cl

API_URL = "http://127.0.0.1:8000/predict"


WELCOME_TEXT = """
# 🌱 AgriBrain AI

Hello, I can help estimate crop yield using simple farm conditions.

**Try this:**  
`rainfall=120, temperature=25, moisture=moderate`

You can use:
- rainfall in mm
- temperature in °C
- moisture as dry, moderate, or wet

Type `help` if you want guidance.
"""


MOISTURE_MAP = {
    "dry": 0.2,
    "low": 0.2,
    "moderate": 0.6,
    "medium": 0.6,
    "normal": 0.6,
    "wet": 0.9,
    "high": 0.9
}


def parse_moisture(value: str) -> float:
    value = value.strip().lower()

    if value in MOISTURE_MAP:
        return MOISTURE_MAP[value]

    try:
        numeric_value = float(value)
        if 0 <= numeric_value <= 1:
            return numeric_value
        raise ValueError
    except ValueError:
        raise ValueError(
            "Soil moisture should be dry, moderate, wet, or a number between 0 and 1."
        )


def parse_user_input(text: str) -> dict:
    values = {}
    parts = text.split(",")

    for part in parts:
        if "=" not in part:
            raise ValueError("Please enter each value using '=' like rainfall=120")

        key, value = part.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        if key in ["rainfall", "rainfall_mm"]:
            try:
                values["rainfall_mm"] = float(value)
            except ValueError:
                raise ValueError("Rainfall should be a number, for example rainfall=120")

        elif key in ["temperature", "temperature_c"]:
            try:
                values["temperature_c"] = float(value)
            except ValueError:
                raise ValueError("Temperature should be a number, for example temperature=25")

        elif key in ["moisture", "soil_moisture", "soil"]:
            values["soil_moisture"] = parse_moisture(value)

        else:
            raise ValueError(f"I do not understand '{key}'. Use rainfall, temperature, and moisture.")

    if "rainfall_mm" not in values:
        raise ValueError("I’m missing rainfall. Example: rainfall=120")

    if "temperature_c" not in values:
        raise ValueError("I’m missing temperature. Example: temperature=25")

    if "soil_moisture" not in values:
        raise ValueError("I’m missing soil moisture. Example: moisture=moderate")

    return values


def moisture_label(value: float) -> str:
    if value <= 0.3:
        return "Dry"
    elif value <= 0.7:
        return "Moderate"
    return "Wet"


@cl.on_chat_start
async def start():
    await cl.Message(content=WELCOME_TEXT).send()


@cl.on_message
async def main(message: cl.Message):
    user_text = message.content.strip()

    try:
        if user_text.lower() in ["help", "instructions", "how do i use this"]:
            await cl.Message(
                content="""
## Let’s do it step by step 🌱

Send your farm conditions like this:

`rainfall=120, temperature=25, moisture=moderate`

Moisture can be:
- `dry`
- `moderate`
- `wet`

Example:
`rainfall=95, temperature=22, moisture=wet`
"""
            ).send()
            return

        if user_text.lower() == "sample":
            user_text = "rainfall=120, temperature=25, moisture=moderate"

        data = parse_user_input(user_text)

        await cl.Message(
            content=(
                "Got it. I’ve received your farm conditions:\n\n"
                f"- Rainfall: **{data['rainfall_mm']} mm**\n"
                f"- Temperature: **{data['temperature_c']} °C**\n"
                f"- Soil moisture: **{moisture_label(data['soil_moisture'])}**\n\n"
                "Let me estimate the likely yield..."
            )
        ).send()

        response = requests.post(API_URL, json=data, timeout=15)
        response.raise_for_status()
        result = response.json()

        predicted_yield = result["predicted_yield"]
        bags_100kg = round(predicted_yield * 10)

        if predicted_yield >= 50:
            yield_level = "High"
            emotional_line = "Good news — your conditions look strong 🌽"
        elif predicted_yield >= 30:
            yield_level = "Moderate"
            emotional_line = "Your conditions look fair, but they need close monitoring 🌿"
        else:
            yield_level = "Low"
            emotional_line = "This looks risky, but it gives you time to adjust before planting ⚠️"

        await cl.Message(
            content=f"""
## ✅ Prediction Result

{emotional_line}

**Yield Level:** {yield_level}  
**Estimated Yield:** {predicted_yield} tons/ha  
**Approx. 100kg Bags:** {bags_100kg} bags per hectare

**Advice:** {result['advice']}

### Your Farm Conditions
- Rainfall: {result['input_received']['rainfall_mm']} mm
- Temperature: {result['input_received']['temperature_c']} °C
- Soil Moisture: {moisture_label(result['input_received']['soil_moisture'])}

Type another set of values, or type `help` for guidance.
"""
        ).send()

    except ValueError as ve:
        await cl.Message(
            content=f"""
## I could not read that clearly

{ve}

Try this:
`rainfall=120, temperature=25, moisture=moderate`

Moisture can be:
- dry
- moderate
- wet

Or type `help` and I’ll guide you.
"""
        ).send()

    except requests.exceptions.ConnectionError:
        await cl.Message(
            content="""
## Backend not connected

Please make sure the backend is running:

`uvicorn main:app --reload`
"""
        ).send()

    except requests.exceptions.Timeout:
        await cl.Message(
            content="The system took too long to respond. Please try again."
        ).send()

    except Exception as e:
        await cl.Message(
            content=f"Something went wrong: {e}"
        ).send()