import os
import hashlib
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Connect to database
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

def clean_phone_number(raw_id: str) -> str:
    """Makes sure the phone number is exactly 10 digits starting with 07 or 01."""
    if raw_id == None or raw_id == "":
        return "0000000000"
    
    # Remove WhatsApp text and country code
    clean_id = raw_id.replace("whatsapp:", "")
    clean_id = clean_id.replace("+254", "0")
    clean_id = clean_id.replace("254", "0")
    clean_id = clean_id.strip()
    
    # Check if it matches our database rules
    if len(clean_id) == 10 and (clean_id.startswith("07") or clean_id.startswith("01")):
        return clean_id
    else:
        return "0000000000"

def extract_advised_action(bot_reply: str) -> str:
    """Reads the bot's reply to guess what action was taken."""
    reply_lower = bot_reply.lower()
    
    if "forward contract" in reply_lower or "twiga" in reply_lower:
        return "Forward Contract"
    elif "loan" in reply_lower or "hustler fund" in reply_lower:
        return "Financial Relief"
    elif "kibarua" in reply_lower or "agent" in reply_lower:
        return "Labor Dispatched"
    else:
        return "General Consultation"

async def log_interaction_to_supabase(session_id: str, user_msg: str, bot_reply: str, location_name: str = "Unknown"):
    """Saves the chat history to the database."""
    try:
        safe_phone = clean_phone_number(session_id)
        advised_action = extract_advised_action(bot_reply)
        
        # Prepare the data dictionary
        payload = {
            "user_phone": safe_phone,
            "user_message": user_msg,
            "bot_response": bot_reply,
            "advised_action_taken": advised_action,
            "location_name": location_name,
            "chat_timestamp": datetime.utcnow().isoformat()
        }
        
        # Insert into the database
        supabase.table('agribrain_chatlogs').insert(payload).execute()
        print(f"Chat logged successfully for: {safe_phone}")
        
    except Exception as e:
        print(f"Error saving chat log: {e}")