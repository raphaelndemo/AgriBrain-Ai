import os
import httpx
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# =========================
# LOAD ENV VARIABLES
# =========================
load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

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
# POST → RECEIVE MESSAGES
# =========================
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()

    try:
        # Log full payload for debugging
        print("\n=== INCOMING PAYLOAD ===")
        print(data)

        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        # Ignore non-message events
        if "messages" not in value:
            return {"status": "no message"}

        message = value["messages"][0]
        contact = value["contacts"][0]

        user_id = contact["wa_id"]
        message_type = message.get("type")

        text = ""
        location = None

        # =========================
        # HANDLE TEXT MESSAGE
        # =========================
        if message_type == "text":
            text = message["text"]["body"]

        # =========================
        # HANDLE LOCATION MESSAGE
        # =========================
        elif message_type == "location":
            location = {
                "lat": message["location"]["latitude"],
                "lon": message["location"]["longitude"]
            }
            text = f"User shared location: {location}"

        # =========================
        # DEFAULT HANDLER
        # =========================
        else:
            text = f"Unsupported message type: {message_type}"

        print(f"USER: {user_id}")
        print(f"MESSAGE: {text}")

        # =========================
        # RESPONSE (MVP: ECHO)
        # =========================
        reply = f"AgriBrain received: {text}"

        # Send response
        await send_whatsapp_message(user_id, reply)

        return {"status": "success"}

    except Exception as e:
        print("ERROR:", str(e))
        return {"status": "error", "message": str(e)}   