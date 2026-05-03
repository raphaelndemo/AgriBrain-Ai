import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase_url: str = os.getenv("SUPABASE_URL")
supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_anon_key)

def mask_phone(phone: str) -> str:
    """Masks phone number for privacy: 0712345678 -> 0712***678"""
    if not phone: return "UNKNOWN"
    phone = str(phone).strip()
    # If standard 10 digit number
    if len(phone) >= 10:
        return phone[:4] + "***" + phone[-3:]
    return phone[:2] + "***" # Fallback for weird formats

def log_telemetry(phone: str, user_message: str, ai_response: str):
    try:
        masked_phone = mask_phone(phone)
        supabase.table("agribrain_chatlogs").insert({
            "user_phone": masked_phone,
            "user_message": user_message,
            "agribrain_response": ai_response
        }).execute()
        print("Telemetry logged securely.")
    except Exception as e:
        print(f"Telemetry Error: {e}")