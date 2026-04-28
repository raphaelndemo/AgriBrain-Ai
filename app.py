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
    "moderate": 0.6,
    "wet": 0.9
}


def parse_moisture(value: str) -> float:
    value = value.strip().lower()

    if value in MOISTURE_MAP:
        return MOISTURE_MAP[value]

    try:
        num = float(value)
        if 0 <= num <= 1:
            return num
    except:
        pass

    raise ValueError("Moisture must be dry, moderate, wet, or a number between 0 and 1.")


def parse_input(text: str) -> dict:
    values = {}
    parts = text.split(",")

    for part in parts:
        if "=" not in part:
            raise ValueError("Use format like rainfall=120")

        key, value = part.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "rainfall":
            values["rainfall_mm"] = float(value)

        elif key == "temperature":
            values["temperature_c"] = float(value)

        elif key == "moisture":
            values["soil_moisture"] = parse_moisture(value)

        else:
            raise ValueError(f"Unknown field: {key}")

    if len(values) != 3:
        raise ValueError("Please include rainfall, temperature, and moisture.")

    return values


def moisture_label(value):
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
    text = message.content.strip()

    try:
        if text.lower() == "help":
            await cl.Message(content="""
## Let’s do it step by step 🌱

Send your farm conditions like this:

`rainfall=120, temperature=25, moisture=moderate`

Moisture can be:
- dry
- moderate
- wet

Example:
`rainfall=95, temperature=22, moisture=wet`
""").send()
            return

        data = parse_input(text)

        await cl.Message(content=f"""
Got it. I’ve received your farm conditions:

- Rainfall: **{data['rainfall_mm']} mm**
- Temperature: **{data['temperature_c']} °C**
- Soil moisture: **{moisture_label(data['soil_moisture'])}**

Analyzing your conditions...
""").send()

        res = requests.post(API_URL, json=data)
        res.raise_for_status()
        result = res.json()

        yield_value = result["predicted_yield"]
        bags = round(yield_value * 10)

        if yield_value >= 5:
            level = "High"
            msg = "Good news — your conditions look strong 🌽"
        elif yield_value >= 2.5:
            level = "Moderate"
            msg = "Your conditions look fair 🌿"
        else:
            level = "Low"
            msg = "Conditions may be challenging ⚠️"

        await cl.Message(content=f"""
## 🌱 Prediction Result

{msg}

**Yield Level:** {level}  
**Estimated Yield:** {yield_value} tons/ha  
**Approx. 100kg Bags:** {bags} bags per hectare  

**Advice:** {result["advice"]}

Type another set of values, or type `help`.
""").send()

    except ValueError as e:
        await cl.Message(content=f"""
I couldn't understand that.

{e}

Try:
`rainfall=120, temperature=25, moisture=moderate`
""").send()

    except requests.exceptions.ConnectionError:
        await cl.Message(content="""
Backend is not running.

Run:
`uvicorn main:app --reload`
""").send()

    except Exception as e:
        await cl.Message(content=f"Error: {e}").send()