import os
import requests
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv

# Import your external logic
from backend_scripts.telemetry import supabase
from backend_scripts.router import process_agribrain_message

load_dotenv()

# Initialize the Router to plug into Chainlit
webhook_router = APIRouter()


VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFICATION_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID") 

def send_whatsapp_message(to: str, text: str):
    """Transmits execution results back to the user edge device."""
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", 
        "to": to, 
        "type": "text", 
        "text": {"body": text}
    }
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}", 
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")

def download_whatsapp_media(media_id: str) -> bytes:
    """Fetches the secure media URL from Meta and downloads the binary image."""
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    # Ask Meta for the secure download URL
    url_request = requests.get(f"https://graph.facebook.com/v17.0/{media_id}", headers=headers)
    if url_request.status_code != 200:
        print(f"Failed to get media URL: {url_request.text}")
        return None
        
    media_url = url_request.json().get("url")
    
    # Download the actual image bytes
    image_request = requests.get(media_url, headers=headers)
    if image_request.status_code == 200:
        return image_request.content
    return None


# routes

@webhook_router.get("/webhook")
async def verify_webhook(request: Request):
    """Handles the Meta Verification Handshake"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return Response(content=challenge, media_type="text/plain")
    
    raise HTTPException(status_code=403, detail="Forbidden")

@webhook_router.post("/webhook")
async def handle_whatsapp_message(request: Request):
    """Data Engineering node for parsing Meta Graph JSON payloads."""
    data = await request.json()
    
    try:
        # Navigate through Meta's nested arrays safely using
        entry = data['entry'][0]['changes'][0]['value']
        
        if 'messages' in entry:
            msg_obj = entry['messages'][0]
            sender_phone = msg_obj['from']
            msg_type = msg_obj.get('type')
            
            incoming_text = ""
            image_bytes = None
            
            # data ingestion and transformation logic based on message type
            
            if msg_type == 'location':
                lat = msg_obj['location']['latitude']
                lon = msg_obj['location']['longitude']
                incoming_text = f"SYSTEM: User dropped a GPS pin at Lat {lat}, Lon {lon}. Analyze this location's soil and weather."
                
            elif msg_type == 'image':
                media_id = msg_obj['image']['id']
                incoming_text = msg_obj['image'].get('caption', "Analyze this farm image.")
                
                # Fetch the image from Meta's servers
                image_bytes = download_whatsapp_media(media_id)
                if not image_bytes:
                    send_whatsapp_message(sender_phone, "Pole, I couldn't download that image. Please try sending it again.")
                    return {"status": "success"}
                    
            elif msg_type == 'text':
                incoming_text = msg_obj['text']['body']
                
                # Intercept the 2FA verification code
                if incoming_text.startswith("Verify AGRI-"):
                    supabase.table("user_profiles").upsert({
                        "phone": sender_phone, 
                        "is_verified": True,
                        "verified_at": datetime.now(timezone.utc).isoformat()
                    }).execute()
                    
                    send_whatsapp_message(sender_phone, "2FA Verified. Dashboard Unlocked. What do you need help with today?")
                    return {"status": "success"}
            else:
                # Ignore unsupported types (audio, documents, etc.) for now
                return {"status": "success"}

            # For the LLM to Pass the cleaned and structured data to the router for AI processing
            
            # Pass the data to your router (ensure process_agribrain_message accepts image_data!)
            if image_bytes:
                ai_response = process_agribrain_message(sender_phone, incoming_text, image_data=image_bytes)
            else:
                ai_response = process_agribrain_message(sender_phone, incoming_text)
                
            # Send AI response back to WhatsApp
            send_whatsapp_message(sender_phone, ai_response)
            
    except (KeyError, IndexError) as e:
        # Catch indexing errors silently so Meta doesn't retry the payload, but log it for debugging
        print(f"Webhook Payload Parsing Error: {e}") 
        
    # Always return a 200 OK so Meta knows the webhook was received
    return {"status": "success"}