import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.memory import ConversationSummaryBufferMemory

from backend_scripts.tools import AGRICULTURAL_TOOLS 
from backend_scripts.telemetry import log_telemetry

primary_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
fallback_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

# Compresses older interactions to preserve token context window
memory = ConversationSummaryBufferMemory(llm=fallback_llm, max_token_limit=1000, memory_key="chat_history", return_messages=True)

system_instructions = """
You are AgriBrain, an elite AI farm management system for Kenyan farmers.
Your core directive is to optimize yields and prevent the Cobweb Phenomenon.
Capabilities: Advise on Mixed Cropping, match farm labor via PostGIS, and analyze wind/UV for spray safety.
Tone: Professional, empathetic. Code-switch naturally with appropriate Swahili or Sheng. Use bullet points.
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

def process_agribrain_message(user_phone: str, message: str) -> str:
    """Executes reasoning matrix with a graceful degradation fallback."""
    try:
        ai_text = primary_executor.invoke({"input": message}).get("output", "Error resolving output.")
    except Exception as e:
        print(f"Primary LLM Failed: {e}. Executing Fallback (Flash)")
        try:
            ai_text = fallback_executor.invoke({"input": message}).get("output", "Error resolving output.")
        except Exception:
            ai_text = "Pole sana, mtandao uko busy kiasi. Please try again in a few minutes."

    log_telemetry(user_phone, message, ai_text)
    return ai_text