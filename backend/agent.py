from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
import os
import json
from utils import debug_print
from pprint import pprint
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel, Field
from typing import Literal

if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

OpenAI_GPT5_Nano = ChatOpenAI(
    model="openai/gpt-5-nano",
    base_url="https://api.aicredits.in/v1",
    api_key=os.getenv("OPENAI_API_KEY")
)

current_model = OpenAI_GPT5_Nano
memory = InMemorySaver()


system_prompt = """
You are a useful agent, reply in one line or less. 
"""

main_agent = create_agent(
    model=current_model,
    system_prompt=system_prompt,
    checkpointer=memory
)
 

def ask_agent(user_input: str):
    debug_print(f"Main agent was invoked with query : {user_input}")
    response = main_agent.invoke({
        "messages": [{"role": "user", "content": user_input}]},
        config={"configurable": {"thread_id": "my_chat"}}
    )
    return response["messages"][-1].content

if __name__ == "__main__":
    user_input = input("Enter your query: ")
    response = ask_agent(user_input)
    print(f"Agent response: {response}")