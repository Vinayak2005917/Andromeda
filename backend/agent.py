from datetime import datetime
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from tools import Get_relevant_webpages, batch_read_pages, update_user, search_images, send_html_response

from utils import debug_print

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")


memory = InMemorySaver()


async def ask_agent(thread_id: str, user_input: str, model_name: str = "deepseek/deepseek-v4-flash", prompt_soul: str | None = None) -> str:

    system_prompt = f'{prompt_soul}\n\nDate and time right now: {datetime.now().strftime("%H:%M:%S on %Y-%m-%d")}'

    current_model = ChatOpenAI(
        model=model_name,
        base_url="https://api.aicredits.in/v1",
        api_key=api_key,
    )
        
    main_agent = create_agent(
        model=current_model,
        tools=[batch_read_pages, Get_relevant_webpages, update_user, search_images, send_html_response],
        system_prompt=system_prompt,
        checkpointer=memory,
    )

    debug_print(f"Main agent using model {model_name} invoked for query '{user_input}' on thread {thread_id}")
    debug_print(f"and system prompt: {system_prompt[:20]}...")
    response = await main_agent.ainvoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return response["messages"][-1].content

if __name__ == "__main__":
    import asyncio

    async def main():
        while True:
            user_input = input("User: ")
            thread_id = input("Thread ID: ")
            response = await ask_agent(thread_id, user_input)
            print(f"Andromeda: {response}")

    asyncio.run(main())
