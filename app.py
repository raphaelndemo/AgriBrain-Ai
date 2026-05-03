import chainlit as cl
from geopy.geocoders import Nominatim
from backend_scripts.router import process_agribrain_message
from backend_scripts.telemetry import supabase

@cl.on_chat_start
async def start_chat():
    # Authentication 
    phone_res = await cl.AskUserMessage(
        content="**HELLO**\nI am **AgriBrain**\nPlease enter your registered phone number (e.g., 0712345678) to log in:", 
        timeout=120
    ).send()
    
    if phone_res:
        phone = phone_res['output'].strip()
        
        # Check Supabase Database
        user_query = supabase.table("user_profiles").select("*").eq("user_phone", phone).execute()
        
        if not user_query.data:
            # The WhatsApp Deep-Link Fallback
            wa_link = "https://wa.me/254742066244?text=Register" # <-- PUT YOUR BOT NUMBER HERE
            await cl.Message(content=f"Account not found.\nTo interact with me, you must first register via our WhatsApp bot. [Click here to open WhatsApp and register]({wa_link})").send()
            return
            
        # 2. Lock Session securely
        cl.user_session.set("phone", phone)
        user_data = user_query.data
        
        # 3. Location Check
        if user_data[0].get("latitude") is None or user_data[0].get("longitude") is None:
            # Valid Dictionary Payload for Chainlit 1.0+
            actions = [cl.Action(name="share_loc", payload={"request": "location"}, label="Share My Location")]
            await cl.Message(content="Login Successful\nI don't have your farm's location. Please share it so we can analyze your local soil and market prices.", actions=actions).send()
        else:
            await cl.Message(content="**Login Successful!**\nYou can type your farming questions, or use the paperclip icon (📎) to upload crop images for disease diagnosis.").send()

@cl.action_callback("share_loc")
async def handle_location(action: cl.Action):
    phone = cl.user_session.get("phone")
    await action.remove() # Removes the button from the chat so they can't click it twice
    
    # Ask the user for their actual town
    res = await cl.AskUserMessage(
        content="Location Setup:\nPlease type the name of your town, village, or county:", 
        timeout=120
    ).send()
    
    if res:
        town_name = res['output'].strip()
        loading_msg = cl.Message(content=f"Locating {town_name} via satellite")
        await loading_msg.send()
        
        # Geocode the town into Lat/Lon
        try:
            geolocator = Nominatim(user_agent="agribrain_web_ui")
            location = geolocator.geocode(f"{town_name}, Kenya")
            
            if location:
                live_lat, live_lon = location.latitude, location.longitude
                
                # 3. Update Supabase with real coordinates
                supabase.table("user_profiles").update({"latitude": live_lat, "longitude": live_lon}).eq("user_phone", phone).execute()
                
                loading_msg.content = f"**Coordinates Locked:** {town_name} (Lat: {live_lat:.4f}, Lon: {live_lon:.4f}).\n\nYour farm profile is complete! What would you like to ask AgriBrain?"
                await loading_msg.update()
                
                # Silently inject the context into the AI's memory
                msg = f"SYSTEM INJECTION: User updated their farm location to {town_name}. Coordinates: Lat {live_lat}, Lon {live_lon}."
                await cl.make_async(process_agribrain_message)(phone, msg)
                
            else:
                loading_msg.content = f"Could not pinpoint '{town_name}' on the map. Please refresh and try a larger nearby town."
                await loading_msg.update()
                
        except Exception as e:
            loading_msg.content = f"Spatial routing offline: {e}"
            await loading_msg.update()

@cl.on_message
async def handle_ui_message(message: cl.Message):
    phone = cl.user_session.get("phone")
    if not phone:
        await cl.Message(content="Please refresh the page and log in first.").send()
        return

    # Multimodal Image Processing (Max 2 images to protect API limits)
    image_bytes_list = []
    if message.elements:
        image_elements = [el for el in message.elements if "image" in el.mime][:2]
        for element in image_elements:
            with open(element.path, "rb") as f:
                image_bytes_list.append(f.read())

    msg = cl.Message(content="Analyzing...")
    await msg.send()

    # Send payload to the LangChain Router
    ai_response = await cl.make_async(process_agribrain_message)(
        user_phone=phone, 
        message_text=message.content, 
        image_data_list=image_bytes_list if image_bytes_list else None
    )
    
    msg.content = ai_response
    await msg.update()