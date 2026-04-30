import os
import requests
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv

from backend_scripts.telemetry import supabase
from backend_scripts.router import process_agribrain_message

load_dotenv()

app = FastAPI(title="AgriBrain Webhook Service")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFICATION_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_ID")

@app.get("/webhook")
async def verify_webhook(request: Request):
    if request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(request.query_params.get("hub.challenge"))
    return Response(content="Forbidden", status_code=403)

@app.post("/webhook")
async def handle_whatsapp_message(request: Request):
    """Data Engineering node for parsing Meta Graph JSON payloads."""
    data = await request.json()
    
    try:
        entry = data['entry']['changes']['value']
        if 'messages' in entry:
            msg_obj = entry['messages']
            sender_phone = msg_obj['from']
            msg_type = msg_obj.get('type')
            
            # SPATIAL DATA INGESTION
            if msg_type == 'location':
                lat = msg_obj['location']['latitude']
                lon = msg_obj['location']['longitude']
                incoming_text = f"SYSTEM: User dropped a GPS pin at Lat {lat}, Lon {lon}. Analyze this location's soil and weather."
            
            # STANDARD TEXT & 2FA INGESTION
            elif msg_type == 'text':
                incoming_text = msg_obj['text']['body']
                
                if incoming_text.startswith("Verify AGRI-"):
                    supabase.table("user_profiles").upsert({
                        "phone": sender_phone, 
                        "is_verified": True,
                        "verified_at": datetime.now(timezone.utc).isoformat()
                    }).execute()
                    send_whatsapp_message(sender_phone, "2FA Verified. Dashboard Unlocked.")
                    return {"status": "success"}
            else:
                return {"status": "success"}

            # Route to LLM Engine
            ai_response = process_agribrain_message(sender_phone, incoming_text)
            send_whatsapp_message(sender_phone, ai_response)
            
    except KeyError:
        pass 
        
    return {"status": "success"}

def send_whatsapp_message(to: str, text: str):
    """Transmits execution results back to the user edge device."""
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
    requests.post(url, json=payload, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"})