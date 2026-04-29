import os
import hashlib
import asyncio
import threading
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

def log_telemetry(phone: str, user_intent: str, ai_response: str):
    """Safely logs telemetry whether running in sync tests or async servers."""
    hashed_id = hashlib.sha256(phone.encode()).hexdigest()[:10]

    def _insert_log():
        try:
            supabase.table("agribrain_chatlogs").insert({
                "user_phone": hashed_id,
                "user_intent": user_intent,
                "bot_response": ai_response
            }).execute()
            print("Telemetry logged successfully.")
        except Exception as e:
            print(f"Telemetry Pipeline Error: {e}")

    # Check if an event loop exists. If yes, use it. If no, use a basic Thread.
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _insert_log)
    except RuntimeError:
        # No event loop (e.g., running raw test.py). Use a standard thread.
        threading.Thread(target=_insert_log).start()