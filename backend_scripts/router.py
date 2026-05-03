import os
import base64
import json, re
import base64
import io
from PIL import Image
from langchain_core import chat_history
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.memory import ConversationSummaryBufferMemory
from backend_scripts.tools import AGRICULTURAL_TOOLS 
from backend_scripts.telemetry import log_telemetry



primary_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
fallback_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

# Compresses older interactions to preserve token context window
memory = ConversationSummaryBufferMemory(llm=fallback_llm, max_token_limit=1000, memory_key="chat_history", return_messages=True)

system_instructions = """
You are AgriBrain, an elite AI farm management system for Kenyan farmers.
Your core directive is to optimize yields and prevent the Cobweb Phenomenon.
Capabilities: Advise on Mixed Cropping, match farm labor via PostGIS, analyze wind/UV for spray safety, AND fetch real-time market commodity prices using your tools.
Tone: Professional, empathetic. Code-switch naturally with appropriate Swahili or Sheng. Use bullet points.
LABOR SOURCING PROTOCOL:
When a farmer discusses planting, harvesting, or farm management, you MUST follow this exact interview flow before running the labor_sourcing_tool:
1. First, ask: "Do you need local vibarua (laborers) to help with this task?"
2. If they say YES: Ask, "Are you available on the ground to supervise their work, or do you need a local Area Agent to manage them for you?"
3. If they need supervision: Run the labor_sourcing_tool with role_needed="AREA_AGENT".
4. If they can supervise themselves: Run the labor_sourcing_tool with role_needed="KIBARUA".

Never assume they need an agent until you ask about their ability to supervise!
"""


prompt = ChatPromptTemplate.from_messages([
    ("system", system_instructions),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

primary_agent = create_tool_calling_agent(primary_llm, AGRICULTURAL_TOOLS, prompt)
primary_executor = AgentExecutor(agent=primary_agent, tools=AGRICULTURAL_TOOLS, memory=memory, verbose=True)

fallback_executor = AgentExecutor(agent=create_tool_calling_agent(fallback_llm, AGRICULTURAL_TOOLS, prompt), tools=AGRICULTURAL_TOOLS, memory=memory, verbose=True)




def process_agribrain_message(user_phone: str, message_text: str, image_data_list: list = None) -> str:
    """
    The Central Brain. Accepts text and an optional list of image bytes.
    """
    try:
        # Build the Multimodal Input
        if image_data_list:
            # If the user didn't type text, provide a default prompt
            safe_text = message_text if message_text.strip() else "Analyze this crop image."
            multimodal_input = [{"type": "text", "text": safe_text}]
            
            # Cap at 2 images to save tokens and prevent overload
            for img_bytes in image_data_list[:2]:
                
                # IMAGE COMPRESSION
                img = Image.open(io.BytesIO(img_bytes))
                if img.mode != 'RGB': 
                    img = img.convert('RGB') # Fixes PNG transparency errors
                    
                img.thumbnail((800, 800)) # Resize to max 800x800
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85) # Compress quality
                compressed_bytes = buffer.getvalue()

                base64_image = base64.b64encode(compressed_bytes).decode('utf-8')
                multimodal_input.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                })
            
            response = primary_executor.invoke({"input": multimodal_input, "chat_history": chat_history})
        else:
            response = primary_executor.invoke({"input": message_text, "chat_history": chat_history})
            
        # Text Extraction
        raw_output = response.get("output", "Error processing response.")
        
        if isinstance(raw_output, list):
            text_parts = [item['text'] for item in raw_output if isinstance(item, dict) and 'text' in item]
            ai_text = " ".join(text_parts) if text_parts else str(raw_output)
        elif isinstance(raw_output, str) and '"text":' in raw_output:
            import re
            try:
                match = re.search(r"'text':\s*'([^']*)'", raw_output)
                ai_text = match.group(1) if match else raw_output
            except:
                ai_text = raw_output
        elif isinstance(raw_output, dict):
            ai_text = raw_output.get('text', str(raw_output))
        else:
            ai_text = str(raw_output)
            
        # Log to Telemetry
        log_telemetry(user_phone, message_text, ai_text)
        
        return ai_text
        
    except Exception as e:
        return f"System Overload. Please try again. ({e})"