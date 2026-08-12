#this script is to learn how memory in langchain/langgraph works.
#in the start it will ask the user if they wanna countinue an old conversation or start a new one.

import os

from typing import Annotated
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages

from utils import debug_print
from dotenv import load_dotenv
load_dotenv()


api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")

OpenAI_GPT5_Nano = ChatOpenAI(
    model="openai/gpt-5-nano",
    base_url="https://api.aicredits.in/v1",
    api_key=api_key
)

class ConversationState(TypedDict):
    messages: Annotated[list, add_messages]

system_prompt = "You are a useful personal assistant. Reply in one line or less"

checkpointer = InMemorySaver()

main_agent = create_agent(
    model=OpenAI_GPT5_Nano,
    system_prompt=system_prompt,
    checkpointer=checkpointer
)


thread_id = input("Enter thread ID (or leave blank to start a new conversation): ")
if thread_id == "":
    thread_id = "chat_" + str(len(checkpointer.list_checkpoints()) + 1)

memory_config = {
    "configurable":{"thread_id": thread_id},
}

while True:
    user_input = input("User: ")
    if user_input.lower() in ["exit", "quit", ""]:
        break
    debug_print(f"Main agent was invoked with query : {user_input}")
    response = main_agent.invoke(
        {"messages": [{"role": "user", "content": user_input}]}, 
        config=memory_config
    )
    print(f"Assistant: {response['messages'][-1].content}")

state = main_agent.get_state(memory_config)

print(f"Conversation state for thread {thread_id}: {state}")