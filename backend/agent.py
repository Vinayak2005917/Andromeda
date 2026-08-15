import os
from contextlib import nullcontext

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from config import settings
from request_context import current_user_id
from tools import (
    Get_relevant_webpages,
    check_date_time,
    read_directory,
    read_file,
    read_webpage,
    write_to_file,
)
from utils import debug_print

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")

current_model = ChatOpenAI(
    model="openai/gpt-5-nano",
    base_url="https://api.aicredits.in/v1",
    api_key=api_key,
)

_checkpointer_context = None
if settings.supabase_db_url:
    from langgraph.checkpoint.postgres import PostgresSaver

    _checkpointer_context = PostgresSaver.from_conn_string(settings.supabase_db_url)
    memory = _checkpointer_context.__enter__()
    memory.setup()
else:
    memory = InMemorySaver()

system_prompt = """
You are Andromeda, a personal assistant useful for daily tasks.
Reply in markdown. Use a little humor, but stay concise and helpful.
The memory tools access only the authenticated user's private memory files.
Ask before writing to memory.
"""

main_agent = create_agent(
    model=current_model,
    tools=[read_directory, read_file, write_to_file, read_webpage, Get_relevant_webpages, check_date_time],
    system_prompt=system_prompt,
    checkpointer=memory,
)


def ask_agent(user_id: str | None, thread_id: str, user_input: str):
    debug_print(f"Main agent invoked for thread {thread_id}")
    token = current_user_id.set(user_id)
    try:
        response = main_agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config={"configurable": {"thread_id": thread_id}},
        )
        return response["messages"][-1].content
    finally:
        current_user_id.reset(token)


def get_thread_messages(thread_id: str) -> list[dict]:
    state = main_agent.get_state({"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", []) if state else []
    result = []
    for message in messages:
        role = getattr(message, "type", "")
        if role not in {"human", "ai"}:
            continue
        content = getattr(message, "content", "")
        if isinstance(content, list):
            content = "".join(str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in content)
        result.append({"role": "user" if role == "human" else "assistant", "content": content})
    return result
