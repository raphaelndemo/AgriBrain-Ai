import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory

from backend.prompts import AGRIBRAIN_SYSTEM_PROMPT
from backend.tools import location_intelligence_tool, market_arbitrage_tool

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")


def initialize_agribrain_agent():
    print("Booting up AgriBrain Core...")

    # =========================
    # LLM (Gemini FIX)
    # =========================
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key,
        temperature=0.4,
        convert_system_message_to_human=True
    )

    # =========================
    # TOOLS
    # =========================
    tools = [
        location_intelligence_tool,
        market_arbitrage_tool
    ]

    # =========================
    # MEMORY
    # =========================
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

    # =========================
    # AGENT (Gemini-compatible)
    # =========================
    agent_executor = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        memory=memory,
        verbose=True,
        agent_kwargs={
            "prefix": AGRIBRAIN_SYSTEM_PROMPT,
            "format_instructions": (
                "Always think step by step. "
                "Use tools when coordinates or location data is needed. "
                "If coordinates are provided, call location_intelligence_tool."
            )
        }
    )

    return agent_executor                               