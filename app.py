import os
import base64
import chainlit as cl
from typing import Optional
from dotenv import load_dotenv

# Import AgriBrain Engine Modules
from backend_scripts.router import initialize_agribrain_agent
from backend_scripts.telemetry import log_interaction_to_supabase

load_dotenv()

# 1.AUTHENTICATIOn
@cl.password_auth_callback
def auth_callback(phone_number: str, password: str) -> Optional[cl.User]:
    """
    Validates the farmer's phone number for persistent session management.
    """
    clean_number = phone_number.replace(" ", "").replace("+254", "0")
    if len(clean_number) >= 10 and clean_number.isdigit():
        return cl.User(identifier=clean_number, metadata={"role": "farmer"})
    return None

# Mock function: In production, this queries the Supabase 'farmer_profiles' table
def fetch_user_profile(phone_number: str):
    return {
        "phone": phone_number,
        "home_location": "Juja", 
        "home_lat": -1.1018, 
        "home_lon": 37.0144
    }

# 2. CHAT cycle
@cl.on_chat_start
async def on_chat_start():
    # Initialize Engine
    engine_executor = initialize_agribrain_agent()
    cl.user_session.set("agent", engine_executor)
    
    # Identify Farmer
    user = cl.user_session.get("user")
    profile = fetch_user_profile(user.identifier)
    cl.user_session.set("profile", profile)
    
    welcome_msg = (
        f"Sasa! I am AgriBrain. 🌾\n\n"
        f"Logged in as: **{user.identifier}**\n"
        f"Home Location: **{profile['home_location']}**\n\n"
        "How can I help you today? You can ask about markets, planting advice, "
        "or upload a photo of your crops for a health check!"
    )
    await cl.Message(content=welcome_msg).send()

@cl.on_message
async def main(message: cl.Message):
    agent = cl.user_session.get("agent")
    profile = cl.user_session.get("profile")
    
    # HANDLE MULTIMODAL IMAGES
    images = [file for file in message.elements if "image" in file.mime]
    
    if images:
        image_file = images
        with open(image_file.path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Structure content for Gemini 
        input_content = [
            {"type": "text", "text": f"[User Home: {profile['home_location']}]\nUser: {message.content}"},
            {"type": "image_url", "image_url": {"url": f"data:{image_file.mime};base64,{image_data}"}}
        ]
    else:
        # Standard Text Input
        input_content = f"[User Home: {profile['home_location']}]\n\nUser: {message.content}"
    
    # EXECUTE AGENT
    async with cl.Step(name="AgriBrain is thinking..."):
        res = await cl.make_async(agent.invoke)({"input": input_content})
        
    final_output = res["output"]
    await cl.Message(content=final_output).send()
    
    # LOG TELEMETRY (Background task)
    await cl.make_async(log_interaction_to_supabase)(
        session_id=user.identifier,
        user_msg=message.content,
        bot_reply=final_output,
        agent_scratchpad=str(res),
        location_name=profile['home_location']
    )