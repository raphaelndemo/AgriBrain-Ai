import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory

from prompts import AGRIBRAIN_SYSTEM_PROMPT
from tools import location_intelligence_tool, get_market_arbitrage

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")


def initialize_agribrain_agent():
    print("Booting up AgriBrain Core...")

    # =========================
    # LLMs
    # =========================
    primary_llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key,
        temperature=0.4
    )

    memory_llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key,
        temperature=0.1
    )

    # =========================
    # TOOLS
    # =========================
    tools = [location_intelligence_tool, get_market_arbitrage]

    # =========================
    # MEMORY
    # =========================
    memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
    )

    # =========================
    # AGENT (COMPATIBLE VERSION)
    # =========================
    agent_executor = initialize_agent(
        tools=tools,
        llm=primary_llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        memory=memory,
        verbose=True
    )

    return agent_executor