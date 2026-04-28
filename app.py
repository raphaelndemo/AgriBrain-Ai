import requests
import chainlit as cl

API_URL = "http://127.0.0.1:8000/predict"

RAIN_OPTIONS = {
    "rain_low": ("Low rainfall", 40),
    "rain_medium": ("Moderate rainfall", 100),
    "rain_high": ("High rainfall", 150),
}

TEMP_OPTIONS = {
    "temp_cool": ("Cool weather", 18),
    "temp_warm": ("Warm weather", 25),
    "temp_hot": ("Hot weather", 32),
}

MOISTURE_OPTIONS = {
    "moisture_dry": ("Dry soil", 0.2),
    "moisture_moderate": ("Moderate soil", 0.6),
    "moisture_wet": ("Wet soil", 0.9),
}


def reset_session():
    cl.user_session.set("rainfall_mm", None)
    cl.user_session.set("temperature_c", None)
    cl.user_session.set("soil_moisture", None)


def get_data():
    return {
        "rainfall_mm": cl.user_session.get("rainfall_mm"),
        "temperature_c": cl.user_session.get("temperature_c"),
        "soil_moisture": cl.user_session.get("soil_moisture"),
    }


def moisture_label(value):
    if value <= 0.3:
        return "Dry"
    if value <= 0.7:
        return "Moderate"
    return "Wet"


async def show_welcome():
    reset_session()

    await cl.Message(
        content="""
**🌱 AgriBrain AI**

Smart crop yield guidance for farmers.

Choose your farm conditions below. No technical typing needed.
"""
    ).send()

    await ask_rainfall()


async def ask_rainfall():
    await cl.Message(
        content="**Step 1 of 3 — Rainfall**\n\nHow is the rainfall in your area?",
        actions=[
            cl.Action(name="rain_low", label="Low", payload={}),
            cl.Action(name="rain_medium", label="Moderate", payload={}),
            cl.Action(name="rain_high", label="High", payload={}),
        ],
    ).send()


async def ask_temperature():
    await cl.Message(
        content="**Step 2 of 3 — Temperature**\n\nHow does the weather feel today?",
        actions=[
            cl.Action(name="temp_cool", label="Cool", payload={}),
            cl.Action(name="temp_warm", label="Warm", payload={}),
            cl.Action(name="temp_hot", label="Hot", payload={}),
        ],
    ).send()


async def ask_moisture():
    await cl.Message(
        content="**Step 3 of 3 — Soil Moisture**\n\nHow does the soil feel?",
        actions=[
            cl.Action(name="moisture_dry", label="Dry", payload={}),
            cl.Action(name="moisture_moderate", label="Moderate", payload={}),
            cl.Action(name="moisture_wet", label="Wet", payload={}),
        ],
    ).send()


async def run_prediction():
    data = get_data()

    await cl.Message(
        content=f"""
**Checking your farm outlook...**

Rainfall: **{data["rainfall_mm"]} mm**  
Temperature: **{data["temperature_c"]} °C**  
Soil moisture: **{moisture_label(data["soil_moisture"])}**
"""
    ).send()

    response = requests.post(API_URL, json=data, timeout=15)
    response.raise_for_status()
    result = response.json()

    yield_value = result["predicted_yield"]
    bags = round(yield_value * 10)

    if yield_value >= 5:
        level = "Strong"
        message = "Good news — your conditions look promising."
    elif yield_value >= 2.5:
        level = "Fair"
        message = "Your conditions look manageable, but they need monitoring."
    else:
        level = "Risky"
        message = "Conditions may be risky right now. You still have time to adjust."

    await cl.Message(
        content=f"""
**🌱 Farm Outlook**

{message}

**Yield level:** {level}  
**Estimated yield:** {yield_value} tons/hectare  
**Approx. harvest:** {bags} bags of 100kg per hectare  

**Advice:** {result["advice"]}

_This is an estimate. Local field advice is still important._
""",
        actions=[
            cl.Action(name="restart", label="Start Again", payload={}),
            cl.Action(name="help", label="Help", payload={}),
        ],
    ).send()


@cl.on_chat_start
async def start():
    await show_welcome()


@cl.action_callback("rain_low")
@cl.action_callback("rain_medium")
@cl.action_callback("rain_high")
async def handle_rain(action: cl.Action):
    label, value = RAIN_OPTIONS[action.name]
    cl.user_session.set("rainfall_mm", value)
    await cl.Message(content=f"Selected: **{label}**").send()
    await ask_temperature()


@cl.action_callback("temp_cool")
@cl.action_callback("temp_warm")
@cl.action_callback("temp_hot")
async def handle_temp(action: cl.Action):
    label, value = TEMP_OPTIONS[action.name]
    cl.user_session.set("temperature_c", value)
    await cl.Message(content=f"Selected: **{label}**").send()
    await ask_moisture()


@cl.action_callback("moisture_dry")
@cl.action_callback("moisture_moderate")
@cl.action_callback("moisture_wet")
async def handle_moisture(action: cl.Action):
    label, value = MOISTURE_OPTIONS[action.name]
    cl.user_session.set("soil_moisture", value)
    await cl.Message(content=f"Selected: **{label}**").send()
    await run_prediction()


@cl.action_callback("restart")
async def restart(action: cl.Action):
    await show_welcome()


@cl.action_callback("help")
async def help_action(action: cl.Action):
    await cl.Message(
        content="""
**How AgriBrain works**

AgriBrain asks 3 simple questions:

1. Rainfall  
2. Temperature  
3. Soil moisture  

Then it estimates the likely farm outlook.
"""
    ).send()


@cl.on_message
async def main(message: cl.Message):
    if message.elements:
        await cl.Message(
            content="""
**Image received.**

Image upload is ready in the interface. In the next version, AgriBrain can analyze crop photos for crop health, pests, or disease signs.
"""
        ).send()
        return

    text = message.content.strip().lower()

    if text in ["help", "guide", "how"]:
        await help_action(None)
    elif text in ["restart", "start again"]:
        await show_welcome()
    else:
        await cl.Message(
            content="Please use the buttons above, or type `restart` to begin again."
        ).send()