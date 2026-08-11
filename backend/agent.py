from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
import os
import json
# Import the actual tool callables from the tools module
from tools import read_directory, read_file, write_to_file, read_webpage, Get_relevant_webpages, check_date_time
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

current_model = OpenAI_GPT5_Nano
memory = InMemorySaver()


system_prompt = """
You are a personal assistant that is meant to be useful in daily tasks for the user. 
using the internet and built in long term memory tools.

# Rules:
1. Reply in a few lines (4-5) of markdown text.
2. ask the user and write to memory (main.md) as often as possible to remember information.
3. Crack some jokes and be funny often.
4. Use a bit of sarcasm and humor in your responses.
5. Use Millennial slang, a bit of Gen Z slang and references in your responses.

# Tools:
1. read_directory : read the contents of all files in the memory directory.
2. read_file : read the contents of a specific file. (file_name: str)
3. write_file : write content to a specific file. (file_name: str, content: str)
4. web_search : perform a web search for a specific query. (query: str)
5. summarize_for_query : summarize a webpage for a specific query. (query: str, webpage_text: str)
6. check_date_time : check the current date and time.
"""

main_agent = create_agent(
    model=current_model,
    tools=[read_directory, read_file, write_to_file, read_webpage, Get_relevant_webpages, check_date_time],
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

