import os
import json
import httpx
import asyncio
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timezone

# Import soil & weather pipeline
from location_context import get_full_location_context

# Import LLM engine
from router import initialize_agribrain_agent

# =========================
# LOAD ENV VARIABLES
# =========================
load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# =========================
# SUPABASE CLIENT
# =========================
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("❌ SUPABASE_URL and SUPABASE_KEY must be set in your .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# BOOT LLM AGENT ONCE ON STARTUP
# Shared across all requests — one agent instance per server
# =========================
print("🚀 Booting AgriBrain LLM Agent...")
agent_executor = initialize_agribrain_agent()
print("✅ AgriBrain Agent Ready.")

app = FastAPI()


# =========================
# GET → WEBHOOK VERIFICATION
# =========================
@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)

    return {"error": "Verification failed"}


# =========================
# SEND MESSAGE TO WHATSAPP
# =========================
async def send_whatsapp_message(to: str, message: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print("SEND ERROR:", response.text)


# =========================
# NORMALIZE PHONE NUMBER
# Table expects: 07XXXXXXXX or 01XXXXXXXX (10 digits)
# WhatsApp sends: 2547XXXXXXXX (international format)
# =========================
def normalize_phone(wa_id: str) -> str:
    if wa_id.startswith("254") and len(wa_id) == 12:
        return "0" + wa_id[3:]
    return wa_id


# =========================
# SAVE CHAT LOG TO SUPABASE
# =========================
def save_chat_log(
    user_phone: str,
    user_message: str,
    bot_response: str,
    location_name: str = None,
    latitude: float = None,
    longitude: float = None,
    crop_intent: str = None,
    soil_data: dict = None,
    weather_data: dict = None,
    expected_harvest_date: str = None,
    advised_action_taken: str = None
):
    try:
        supabase.table("agribrain_chatlogs").insert({
            "user_phone": normalize_phone(user_phone),
            "user_message": user_message,
            "bot_response": bot_response,
            "location_name": location_name,
            "latitude": latitude,
            "longitude": longitude,
            "crop_intent": crop_intent,
            "soil_data": soil_data,
            "weather_data": weather_data,
            "expected_harvest_date": expected_harvest_date,
            "advised_action_taken": advised_action_taken,
            "chat_timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()
        print(f"✅ Chat log saved for {user_phone}")

    except Exception as e:
        print(f"Memory save error: {e}")


# =========================
# FETCH CONVERSATION HISTORY
# =========================
def get_conversation_history(user_phone: str, limit: int = 5) -> list:
    try:
        phone = normalize_phone(user_phone)
        result = (
            supabase.table("agribrain_chatlogs")
            .select("user_message, bot_response, location_name, crop_intent, chat_timestamp")
            .eq("user_phone", phone)
            .order("chat_timestamp", desc=True)
            .limit(limit)
            .execute()
        )

        history = []
        for row in result.data[::-1]:
            history.append({"role": "user", "content": row["user_message"]})
            history.append({"role": "assistant", "content": row["bot_response"]})

        return history

    except Exception as e:
        print(f"Memory fetch error: {e}")
        return []


# =========================
# GEOCODING (Place Name → Coordinates)
# =========================
async def geocode_location(place_name: str) -> dict | None:
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{place_name}, Kenya",
        "format": "json",
        "limit": 1
    }
    headers = {"User-Agent": "AgriBrain-Student-Project/1.0"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=10.0)
            results = response.json()

            if results:
                return {
                    "lat": float(results[0]["lat"]),
                    "lon": float(results[0]["lon"]),
                    "display_name": results[0]["display_name"]
                }
    except Exception as e:
        print(f"Geocoding error: {e}")

    return None


# =========================
# FORMAT LOCATION REPORT
# Turns JSON from location_context.py into readable WhatsApp message
# =========================
def format_location_report(context_json: str, location_name: str = None) -> str:
    try:
        data = json.loads(context_json)

        if "error" in data:
            return f"⚠️ Could not fetch location data: {data['error']}"

        soil = data.get("soil", {})
        weather = data.get("weather", {})
        loc = data.get("location", {})

        location_line = (
            f"📍 *{location_name}*\n"
            if location_name
            else f"📍 *Coordinates: {loc.get('latitude')}, {loc.get('longitude')}*\n"
        )

        report = (
            f"🌱 *AgriBrain Location Analysis*\n\n"
            f"{location_line}\n"
            f"🪱 *Soil Data (0-20cm depth)*\n"
            f"  • pH: {soil.get('ph')}\n"
            f"  • Nitrogen: {soil.get('nitrogen_g_per_kg')} g/kg\n"
            f"  • Clay Content: {soil.get('clay_content_percent')}%\n"
            f"  • Organic Carbon: {soil.get('organic_carbon_g_per_kg')} g/kg\n"
            f"  • Phosphorus: {soil.get('phosphorus_ppm')} ppm\n\n"
            f"🌤️ *Weather (Current)*\n"
            f"  • Temperature: {weather.get('temperature_c')}°C\n"
            f"  • 7-day Rainfall: {weather.get('rainfall_7day_mm')} mm\n\n"
            f"💬 What would you like to plant? I'll check if it's a good fit!"
        )

        return report

    except Exception as e:
        print(f"Format error: {e}")
        return "⚠️ Error formatting location report. Please try again."


# =========================
# CALL LLM AGENT
# Runs in a thread so it doesn't block the async event loop
# agent_executor uses LangChain memory internally — history is managed by it
# =========================
async def call_llm_agent(message: str) -> str:
    try:
        # agent_executor.invoke() is synchronous (LangChain)
        # run_in_executor prevents it from blocking FastAPI's event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: agent_executor.invoke({"input": message})
        )
        return result.get("output", "I couldn't generate a response. Please try again.")

    except Exception as e:
        print(f"LLM error: {e}")
        return "⚠️ AgriBrain is thinking too hard right now. Please try again in a moment."


# =========================
# VERIFICATION INTERCEPT
# =========================
async def handle_verification(user_id: str, text: str):
    try:
        supabase.table("user_profiles").upsert({
            "phone": normalize_phone(user_id),
            "is_verified": True,
            "verified_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        reply = "✅ Number verified successfully! Your AgriBrain web app is now unlocked for 30 days."

    except Exception as e:
        print(f"Verification error: {e}")
        reply = "⚠️ Verification failed. Please try again."

    await send_whatsapp_message(user_id, reply)


# =========================
# HANDLE TEXT MESSAGE
# =========================
async def handle_text(user_id: str, text: str):
    location_name = None
    latitude = None
    longitude = None
    soil_data_dict = None
    weather_data_dict = None

    # --- STEP 1: Check if message contains a place name ---
    geocode_keywords = [
        "nina shamba", "niko", "nina ardhi", "location",
        "place", "area", "farm in", "farming in"
    ]

    if any(kw in text.lower() for kw in geocode_keywords):
        words = text.split()
        place_guess = words[-1]
        coords = await geocode_location(place_guess)

        if coords:
            location_name = coords["display_name"]
            latitude = coords["lat"]
            longitude = coords["lon"]

            # Acknowledge immediately — soil/weather fetch takes a few seconds
            await send_whatsapp_message(
                user_id,
                f"📍 Found *{coords['display_name']}*\nFetching soil and weather data..."
            )

            # Fetch soil & weather
            context_json = await get_full_location_context(latitude, longitude)

            # Parse for Supabase storage
            try:
                context_data = json.loads(context_json)
                soil_data_dict = context_data.get("soil")
                weather_data_dict = context_data.get("weather")
            except Exception:
                pass

            # Build enriched message for LLM — include soil/weather as context
            enriched_message = (
                f"The farmer said: '{text}'\n\n"
                f"Location identified: {location_name}\n"
                f"Here is the real-time soil and weather data for this location:\n"
                f"{context_json}\n\n"
                f"Use this data to give a crop recommendation."
            )

            # Pass to LLM agent
            reply = await call_llm_agent(enriched_message)

        else:
            reply = (
                f"📍 I couldn't find *{place_guess}* on the map. "
                f"Could you drop a location pin instead?\n"
                f"(Tap the 📎 icon → Location)"
            )

    else:
        # --- STEP 2: No location keyword — pass directly to LLM ---
        reply = await call_llm_agent(text)

    save_chat_log(
        user_phone=user_id,
        user_message=text,
        bot_response=reply,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        soil_data=soil_data_dict,
        weather_data=weather_data_dict
    )

    await send_whatsapp_message(user_id, reply)


# =========================
# HANDLE LOCATION PIN
# =========================
async def handle_location(user_id: str, lat: float, lon: float):
    # Immediate acknowledgement
    await send_whatsapp_message(
        user_id,
        "📍 Got your location pin! Fetching soil and weather data..."
    )

    # Fetch soil & weather
    context_json = await get_full_location_context(lat, lon)

    # Parse for Supabase storage
    soil_data_dict = None
    weather_data_dict = None
    try:
        context_data = json.loads(context_json)
        soil_data_dict = context_data.get("soil")
        weather_data_dict = context_data.get("weather")
    except Exception:
        pass

    # Build enriched message for LLM
    enriched_message = (
        f"The farmer dropped a location pin at coordinates ({lat}, {lon}).\n\n"
        f"Here is the real-time soil and weather data for this location:\n"
        f"{context_json}\n\n"
        f"Introduce yourself briefly, summarize the conditions, "
        f"and ask what they would like to plant."
    )

    # Pass to LLM agent
    reply = await call_llm_agent(enriched_message)

    save_chat_log(
        user_phone=user_id,
        user_message=f"[Location pin: {lat}, {lon}]",
        bot_response=reply,
        latitude=lat,
        longitude=lon,
        soil_data=soil_data_dict,
        weather_data=weather_data_dict
    )

    await send_whatsapp_message(user_id, reply)


# =========================
# HANDLE IMAGE/MEDIA
# =========================
async def handle_image(user_id: str):
    reply = (
        "📸 I can see you've sent an image! "
        "Crop disease detection via photo is coming soon. "
        "For now, please describe your crop issue in text and I'll help you."
    )

    save_chat_log(
        user_phone=user_id,
        user_message="[Image received]",
        bot_response=reply
    )

    await send_whatsapp_message(user_id, reply)


# =========================
# POST → RECEIVE MESSAGES
# =========================
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()

    try:
        print("\n=== INCOMING PAYLOAD ===")
        print(data)

        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return {"status": "ignored"}

        message = value["messages"][0]
        contact = value["contacts"][0]

        user_id = contact["wa_id"]
        message_type = message.get("type")

        print(f"USER: {user_id} | TYPE: {message_type}")

        if message_type == "text":
            text = message["text"]["body"]
            print(f"MESSAGE: {text}")

            if text.startswith("Verify AGRI-"):
                await handle_verification(user_id, text)
            else:
                await handle_text(user_id, text)

        elif message_type == "location":
            lat = message["location"]["latitude"]
            lon = message["location"]["longitude"]
            print(f"LOCATION: {lat}, {lon}")
            await handle_location(user_id, lat, lon)

        elif message_type in ["image", "document"]:
            await handle_image(user_id)

        else:
            await send_whatsapp_message(
                user_id,
                "⚠️ Sorry, I can only process text messages and location pins for now."
            )

        return {"status": "success"}

    except Exception as e:
        print("ERROR:", str(e))

        try:
            user_id = data["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
            await send_whatsapp_message(
                user_id,
                "⚠️ Something went wrong on our end. Please try again in a moment."
            )
        except Exception:
            pass

        return {"status": "error", "message": str(e)}