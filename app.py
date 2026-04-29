import os
import random
from datetime import datetime, timezone
from dotenv import load_dotenv
import chainlit as cl

# Import internal backend routing
from backend_scripts.router import process_agribrain_message
from backend_scripts.telemetry import supabase 

load_dotenv()

BOT_PHONE_NUMBER = os.getenv("BOT_PHONE_NUMBER")

# ==========================================
# PHASE 2: GEMINI-STYLE ACTION STARTERS
# ==========================================
@cl.set_starters
async def set_starters():
    return [
        cl.Starter(label="Mixed Cropping", message="Plan a mixed cropping strategy for 2 acres to minimize climate risk.", icon="/public/icons/plant.svg"),
        cl.Starter(label="Market Arbitrage", message="Check the current market prices and tell me the best county to sell maize today.", icon="/public/icons/market.svg"),
        cl.Starter(label="Find Farm Labor", message="I need farm laborers within a 10km radius. What are the regional rates?", icon="/public/icons/labor.svg")
    ]

# ==========================================
# AUTHENTICATION & SESSION STATE
# ==========================================
@cl.on_chat_start
async def on_start():
    # 1. Ask for the phone number synchronously
    res = await cl.AskUserMessage(
        content="🌾 **AgriBrain Enterprise**\n\nEnter your WhatsApp number (e.g., 254700000000) to initialize your stateful session.",
        timeout=120
    ).send()
    
    if res:
        phone_number = res['output'].strip()
        cl.user_session.set("user_phone", phone_number)
        
        try:
            # 2. Check DB synchronously (Fast enough that it won't break the UI)
            profile_check = supabase.table("user_profiles").select("is_verified, verified_at").eq("phone", phone_number).execute()
            
            if profile_check.data and profile_check.data.get("is_verified"):
                verified_at_str = profile_check.data.get("verified_at")
                if verified_at_str:
                    verified_at = datetime.fromisoformat(verified_at_str.replace('Z', '+00:00'))
                    days_since_verification = (datetime.now(timezone.utc) - verified_at).days
                    
                    if days_since_verification < 30:
                        cl.user_session.set("is_verified", True)
                        await cl.Message(content="✅ **Session Restored.** How can AgriBrain help you today?").send()
                        return 
            
            # 3. Trigger Handshake
            cl.user_session.set("is_verified", False)
            supabase.table("user_profiles").upsert({"phone": phone_number, "is_verified": False}).execute()
            
            verify_code = f"AGRI-{random.randint(1000, 9999)}"
            wa_link = f"https://wa.me/{BOT_PHONE_NUMBER}?text=Verify%20{verify_code}"
            
            await cl.Message(
                content=f"**🔒 2FA Required**\n1. [Click Here to Authenticate via WhatsApp]({wa_link})\n2. Send the pre-filled verification code.\n3. **Type 'Done' here** once you have sent the WhatsApp message."
            ).send()
            
        except Exception as e:
            await cl.Message(content=f"⚠️ Database Connection Error. Ensure your SUPABASE_URL is correct in the .env file. Details: {e}").send()


@cl.on_message
async def on_message(message: cl.Message):
    user_phone = cl.user_session.get("user_phone")
    is_verified = cl.user_session.get("is_verified")

    if not is_verified:
        if message.content.strip().lower() == "done":
            try:
                check = supabase.table("user_profiles").select("is_verified").eq("phone", user_phone).execute()
                
                if check.data and check.data.get("is_verified") == True:
                    cl.user_session.set("is_verified", True)
                    await cl.Message(content="✅ **Handshake Confirmed!** System unlocked. What do you need?").send()
                else:
                    await cl.Message(content="⏳ We haven't received the webhook yet. Please ensure you sent the WhatsApp message, then type 'Done' again.").send()
            except Exception as e:
                 await cl.Message(content=f"⚠️ Check failed: {e}").send()
            return
        else:
            await cl.Message(content="🔒 Access Denied. Please verify via WhatsApp and type 'Done'.").send()
            return

    # Process verified queries
    try:
        # We process the LLM synchronously to avoid ContextVar errors during streaming
        ai_response = process_agribrain_message(user_phone, message.content)
        await cl.Message(content=ai_response).send()
    except Exception as e:
        await cl.Message(content=f"⚠️ LLM Processing Error: {e}").send()