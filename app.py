import os
import random
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv

import chainlit as cl

# Import your existing database and AI logic
# Make sure tools.py and router.py are in the same directory
from tools import supabase
from router import process_agribrain_message

load_dotenv()

# --- CONFIGURATION ---
# The phone number Meta assigned to your WhatsApp bot
BOT_PHONE_NUMBER = os.getenv("BOT_PHONE_NUMBER") 

# ==========================================
# CHAINLIT WEB UI (FRONTEND)
# ==========================================

@cl.on_chat_start
async def on_start():
    """Handles web user login and enforces the 30-Day Deep Link Verification."""
    
    # Send welcome message and ask for the phone number
    res = await cl.AskUserMessage(
        content="🌾 **Welcome to the AgriBrain Dashboard**\n\nPlease enter your WhatsApp number (e.g., 254700000000) to securely log in.",
        timeout=120
    ).send()
    
    if res:
        phone_number = res['output'].strip()
        cl.user_session.set("user_phone", phone_number)
        
        # 1. Check existing verification status in Supabase
        profile_check = supabase.table("user_profiles").select("is_verified, verified_at").eq("phone", phone_number).execute()
        
        if profile_check.data and profile_check.data.get("is_verified"):
            verified_at_str = profile_check.data.get("verified_at")
            
            if verified_at_str:
                # Convert Supabase ISO string to Python datetime object
                verified_at = datetime.fromisoformat(verified_at_str.replace('Z', '+00:00'))
                days_since_verification = (datetime.now(timezone.utc) - verified_at).days
                
                # 2. Rolling Session Check: If < 30 days, bypass verification
                if days_since_verification < 30:
                    cl.user_session.set("is_verified", True)
                    await cl.Message(
                        content=f"✅ **Welcome back!** Your session is active (Expires in {30 - days_since_verification} days).\n\nHow can the AgriBrain agent assist your farm today?"
                    ).send()
                    return 
        
        # 3. If no profile or token expired, trigger the wa.me authentication flow
        cl.user_session.set("is_verified", False)
        
        # Reset the user's status in the database to await new verification
        supabase.table("user_profiles").upsert({"phone": phone_number, "is_verified": False}).execute()
        
        verify_code = f"AGRI-{random.randint(1000, 9999)}"
        # Format the deep link with URL-encoded spaces
        wa_link = f"https://wa.me/{BOT_PHONE_NUMBER}?text=Verify%20{verify_code}"
        
        await cl.Message(
            content=(
                "**🔒 Security Verification Required**\n"
                "Your session has expired or you are a new user. Click the link below to verify via WhatsApp:\n\n"
                f"🔗 **[Click Here to Verify]({wa_link})**\n\n"
                "*Awaiting secure handshake from the webhook...*"
            )
        ).send()

        # 4. Asynchronous Polling Loop: Listen for webhook updates in Supabase
        verified = False
        for _ in range(30): # Polls for 60 seconds (30 checks * 2 seconds)
            await asyncio.sleep(2)
            
            check = supabase.table("user_profiles").select("is_verified").eq("phone", phone_number).execute()
            if check.data and check.data.get("is_verified") == True:
                verified = True
                cl.user_session.set("is_verified", True)
                break
        
        if verified:
            await cl.Message(content="✅ **Handshake Successful!** The system is now unlocked. What agricultural data do you need?").send()
        else:
            await cl.Message(content="⏳ Verification timed out. Please refresh the browser page to try again.").send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handles standard AI chat queries post-verification."""
    is_verified = cl.user_session.get("is_verified")
    user_phone = cl.user_session.get("user_phone")

    # Hard security block
    if not is_verified:
        await cl.Message(content="🔒 Access Denied. Please verify your WhatsApp number first.").send()
        return

    # Pass the query to the LangChain routing engine
    ai_response = process_agribrain_message(user_phone, message.content)
    
    # Stream or display the response back to the Chainlit UI
    await cl.Message(content=ai_response).send()