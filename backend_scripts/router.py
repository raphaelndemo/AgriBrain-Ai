import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationSummaryBufferMemory

from backend_engine.prompts import AGRIBRAIN_SYSTEM_PROMPT
from backend_engine.tools import location_intelligence_tool, get_market_arbitrage

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def initialize_agribrain_agent():
    print("Booting up AgriBrain Core...")
    
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
    
    tools = [location_intelligence_tool, get_market_arbitrage]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", AGRIBRAIN_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"), 
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"), 
    ])
    
    agribrain_memory = ConversationSummaryBufferMemory(
        llm=memory_llm,
        max_token_limit=1000, 
        memory_key="chat_history",
        return_messages=True
    )
    
    agent = create_tool_calling_agent(primary_llm, tools, prompt)
    
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        memory=agribrain_memory,
        verbose=True 
    )
    
    return agent_executor