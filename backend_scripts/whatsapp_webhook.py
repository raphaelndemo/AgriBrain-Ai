import os
import httpx
from fastapi import FastAPI, Request, HTTPException, Response
from dotenv import load_dotenv
from backend_scripts.router import process_agribrain_message
from backend_scripts.telemetry import supabase

# Load environment variables
load_dotenv()
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID") # Found in Meta App Dashboard
WHATSAPP_VERIFICATION_TOKEN = os.getenv("WHATSAPP_VERIFICATION_TOKEN", "agribrain_secure_123") # You set this in Meta Dashboard

app = FastAPI(title="AgriBrain WhatsApp Node")

# HELPER FUNCTIONS
async def send_whatsapp_message(to_phone: str, text: str):
    """Sends the AI's response back to the farmer via Meta Graph API."""
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text}
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)

async def download_meta_image(media_id: str) -> bytes:
    """Securely downloads image bytes from Meta's servers."""
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    async with httpx.AsyncClient() as client:
        # 1. Ask Meta for the specific image URL
        res = await client.get(f"https://graph.facebook.com/v18.0/{media_id}", headers=headers)
        res.raise_for_status()
        media_url = res.json().get("url")
        
        # 2. Download the actual binary image data
        img_res = await client.get(media_url, headers=headers)
        img_res.raise_for_status()
        return img_res.content

# WEBHOOK ENDPOINTS
@app.get("/webhook")
async def verify_webhook(request: Request):
    """Required by Meta to authorize the webhook URL."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode and token:
        if mode == "subscribe" and token == WHATSAPP_VERIFICATION_TOKEN:
            return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Invalid verification token")

@app.post("/webhook")
async def whatsapp_listener(request: Request):
    """The main ingestion engine for all WhatsApp payloads."""
    try:
        data = await request.json()
        
        # Safely navigate Meta's massive JSON payload structure
        if "entry" in data and data["entry"].get("changes"):
            value = data["entry"]["changes"]["value"]
            
            if "messages" in value:
                message = value["messages"]
                phone = message["from"]
                msg_type = message["type"]
                
                # 1. Auto-Registration Check
                user_query = supabase.table("user_profiles").select("*").eq("user_phone", phone).execute()
                if not user_query.data:
                     # Silently register new users so DB logs don't crash
                     supabase.table("user_profiles").insert({"user_phone": phone, "is_verified": True}).execute()

                # 2. Route based on Message Type
                ai_response = ""
                
                if msg_type == "location":
                    lat = message["location"]["latitude"]
                    lon = message["location"]["longitude"]
                    
                    # Instantly save to Supabase
                    supabase.table("user_profiles").update({"latitude": lat, "longitude": lon}).eq("user_phone", phone).execute()
                    
                    text_payload = f"SYSTEM INJECTION: User dropped a GPS pin at Lat: {lat}, Lon: {lon}. Acknowledge and analyze the region."
                    ai_response = process_agribrain_message(phone, text_payload)
                    
                elif msg_type == "image":
                    image_id = message["image"]["id"]
                    image_bytes = await download_meta_image(image_id)
                    
                    # Check if they sent text WITH the image
                    caption = message.get("image", {}).get("caption", "Analyze this crop image.")
                    ai_response = process_agribrain_message(phone, caption, [image_bytes])
                    
                elif msg_type == "text":
                    text_payload = message["text"]["body"]
                    ai_response = process_agribrain_message(phone, text_payload)
                
                else:
                    ai_response = "I currently only support text messages, photos of crops, and GPS location pins."

                # 3. Send the AI's final answer back to WhatsApp
                if ai_response:
                    await send_whatsapp_message(phone, ai_response)
                
    except Exception as e:
        print(f"Webhook Isolation Caught Error: {e}")
        
    # Meta requires a 200 OK response within seconds, regardless of what happens
    return {"status": "ok"}