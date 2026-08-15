import os
from datetime import datetime

import requests
from ddgs import DDGS
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from memory_store import append_memory, list_memory, read_memory
from request_context import require_user_id
from utils import debug_print
from websocket import send_tool_update

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")


@tool("check_date_time", description="Check the current date and time.")
def check_date_time():
    return datetime.now().strftime("%H:%M:%S on %Y-%m-%d")


@tool("read_directory", description="Read the contents of all files in the user's private memory.")
def read_directory(reason: str):
    send_tool_update(f"Reading memory for reason: {reason}")
    try:
        result = list_memory(require_user_id())
        send_tool_update("Done reading memory")
        return result
    except Exception as exc:
        send_tool_update(f"Error reading memory: {exc}")
        return str(exc)


@tool("Read_file", description="Read one of the user's private memory files: user.md, notes.md, or logs.md.")
def read_file(file_name: str):
    send_tool_update(f"Reading file {file_name}")
    try:
        result = read_memory(require_user_id(), file_name)
        send_tool_update(f"Done reading file {file_name}")
        return result
    except Exception as exc:
        send_tool_update(f"Error reading file {file_name}: {exc}")
        return str(exc)


@tool("write_to_file", description="Append content to one of the user's private memory files.")
def write_to_file(file_name: str, content: str) -> str:
    send_tool_update(f"Appending to {file_name}, content: {content[:50]}...")
    try:
        result = append_memory(require_user_id(), file_name, content)
        send_tool_update(f"Appended to file {file_name}")
        return result
    except Exception as exc:
        send_tool_update(f"Error writing file {file_name}: {exc}")
        return str(exc)


OpenAI_GPT5_Nano = ChatOpenAI(
    model="openai/gpt-5-nano",
    base_url="https://api.aicredits.in/v1",
    api_key=api_key,
)


def summarize_for_query(query, webpage_text):
    response = OpenAI_GPT5_Nano.invoke(f"Extract only facts relevant to this question: {query}\n\n{webpage_text}")
    return response.content


@tool("Read_webpage", description="Read and summarize a webpage based on the user's query.")
def read_webpage(url: str, query: str):
    send_tool_update(f"Reading webpage {url[:40]}")
    response = requests.get(f"https://r.jina.ai/{url}", timeout=30)
    return summarize_for_query(query, response.text)[:6000]


@tool("Get_relevant_webpages", description="Search the web for relevant webpages.")
def Get_relevant_webpages(query: str):
    send_tool_update(f"Searching the web for: {query}")
    results = DDGS().text(query, max_results=5)
    return "\n\n".join(
        f"Title: {item['title']}\nLink: {item['href']}\nDescription: {item['body']}"
        for item in results
    )
