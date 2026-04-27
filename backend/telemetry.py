import os
import hashlib
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

def anonymize_farmer_id(raw_id: str) -> str:
    """Hashes the user ID to ensure privacy (e.g., '#FARMER-a1b2c3')."""
    if not raw_id:
        return "#FARMER-UNKNOWN"
    hashed = hashlib.sha256(raw_id.encode()).hexdigest()[:6]
    return f"#FARMER-{hashed.upper()}"

def extract_advised_action(bot_reply: str, scratchpad: str) -> str:
    """Parses the bot's response and internal thoughts to categorize the advice given."""
    reply_lower = bot_reply.lower()
    scratchpad_lower = scratchpad.lower()
    
    if "hustler fund" in reply_lower or "subsidy" in reply_lower or "loan" in reply_lower:
        return "Financial Relief"
    elif "forward contract" in reply_lower:
        return "Forward Contract"
    elif "arbitrage" in scratchpad_lower or "sell at" in reply_lower:
        return "Market Arbitrage"
    elif "geocode" in scratchpad_lower or "invest" in reply_lower:
        return "Land Investment Advice"
    elif "disease" in reply_lower or "treatment" in reply_lower:
        return "Agronomy/Disease Treatment"
    
    return "General Consultation"

async def log_interaction_to_supabase(session_id: str, user_msg: str, bot_reply: str, agent_scratchpad: str, location_name: str = "Unknown"):
    """
    Asynchronous function called by Chainlit after the bot replies. 
    Builds the payload and pushes it to the agribrain_chatlogs table.
    """
    try:
        farmer_id = anonymize_farmer_id(session_id)
        advised_action = extract_advised_action(bot_reply, agent_scratchpad)
        
        # Build the structured telemetry payload
        payload = {
            "farmer_id": farmer_id,
            "user_message": user_msg,
            "bot_response": bot_reply,
            "advised_action_taken": advised_action,
            "location_name": location_name,
            # If you are capturing specific crop intents or lat/lon directly from the UI, 
            # you can pass them into this function and assign them here.
            "chat_timestamp": datetime.utcnow().isoformat()
        }
        
        # Push to the database asynchronously
        supabase.table('agribrain_chatlogs').insert(payload).execute()
        print(f"User successfully logged for {farmer_id} | Action: {advised_action}")
        
    except Exception as e:
        print(f"Failed to log telemetry: {e}")