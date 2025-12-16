import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver  # Use SqliteSaver for disk persistence
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model


async def main():
    # 1. Initialize multi-server client
    client = MultiServerMCPClient({
        "postgres": {"transport": "stdio", "command": "python", "args": ["mcp-servers/postgres/server.py"]},
        "competitor": {"transport": "stdio", "command": "python", "args": ["mcp-servers/competitor-simulator/server.py"]},
        "social": {"transport": "stdio", "command": "python", "args": ["mcp-servers/social-simulator/server.py"]},
        "weather": {"transport": "stdio", "command": "python", "args": ["mcp-servers/weather-simulator/server.py"]}
    })

    # 2. Setup Tools and Memory
    tools = await client.get_tools()
    memory = InMemorySaver()  # This stores the conversation history in RAM
    
    # 3. Create Agent with Memory
    llm = ChatOpenAI(model="gpt-5-mini", api_key=os.getenv("OPENAI_API_KEY"))
    # llm = init_chat_model("google_genai:gemini-2.0-flash")
    
    agent = create_agent(llm, tools, checkpointer=memory)

    # 4. Stateful Chat Loop
    config = {"configurable": {"thread_id": "user_123"}}  # Unique ID for this session
    
    print("Stateful MCP Chatbot Ready! (Thread: user_123)")
    while True:
        query = input("\nYou: ").strip()
        if query.lower() in ["quit", "exit"]:
            break
            
        # The agent now looks up 'user_123' in the checkpointer to load history
        response = await agent.ainvoke({"messages": [("user", query)]}, config=config)
        print(f"\nAssistant: {response['messages'][-1].content}")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
