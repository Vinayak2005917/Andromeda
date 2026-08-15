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
from websocket import send_tool_update, send_user_update, send_HTML

import serpapi
import os



load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
serpapi_client = serpapi.Client(api_key=os.getenv("SERP_API_KEY"))
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")
if not os.getenv("SERP_API_KEY"):
    raise RuntimeError("SERP_API_KEY is not set")


@tool("update_user", description="Update the user about the progress you have made so far on the task you are working on.")
def update_user(content: str):
    debug_print(f"Sending update to user: {content}")
    send_user_update(f"Update: {content}")
    return f"Update sent to user: {content}"


@tool("read_directory", description="Read the contents of all files in the user's private memory.")
def read_directory(reason: str):
    debug_print(f"Reading memory for reason: {reason}")
    send_tool_update(f"Reading memory for reason: {reason}")
    try:
        result = list_memory(require_user_id())
        send_tool_update("Done reading memory")
        return result
    except Exception as exc:
        debug_print(f"Error reading memory: {exc}")
        return str(exc)


@tool("Read_file", description="Read one of the user's private memory files: user.md, notes.md, or logs.md.")
def read_file(file_name: str):
    debug_print(f"Reading file {file_name}")
    send_tool_update(f"Reading file {file_name}")
    try:
        result = read_memory(require_user_id(), file_name)
        debug_print(f"Done reading file {file_name}")
        send_tool_update(f"Done reading file {file_name}")
        return result
    except Exception as exc:
        debug_print(f"Error reading file {file_name}: {exc}")
        return str(exc)


@tool("write_to_file", description="Append content to one of the user's private memory files.")
def write_to_file(file_name: str, content: str) -> str:
    send_tool_update(f"Appending to {file_name}, content: {content[:50]}...")
    debug_print(f"Appending to {file_name}, content: {content[:50]}...")
    try:
        result = append_memory(require_user_id(), file_name, content)
        debug_print(f"Appended to file {file_name}")
        send_tool_update(f"Appended to file {file_name}")
        return result
    except Exception as exc:
        debug_print(f"Error writing file {file_name}: {exc}")
        return str(exc)


OpenAI_GPT5_Nano = ChatOpenAI(
    model="openai/gpt-5-nano",
    base_url="https://api.aicredits.in/v1",
    api_key=api_key,
)


def summarize_for_query(query, webpage_text):
    response = OpenAI_GPT5_Nano.invoke(f"Summarize the information relevant to this question: {query}\n\n{webpage_text}")
    return response.content


@tool("Read_webpage", description="Read and summarize a webpage based on the user's query.")
def read_webpage(url: str, query: str):
    debug_print(f"Reading webpage {url[:100]}")
    send_tool_update(f"Reading webpage {url[:40]}")
    response = requests.get(f"https://r.jina.ai/{url}", timeout=30)
    return summarize_for_query(query, response.text)[:6000]


@tool("Get_relevant_webpages", description="Search the web for relevant webpages.")
def Get_relevant_webpages(query: str):
    debug_print(f"Searching the web for: {query}")
    send_tool_update(f"Searching the web for: {query}")
    results = DDGS().text(query, max_results=5)
    debug_print(f"Found & Sent {len(results)} results for query: {query}")
    return "\n\n".join(
        f"Title: {item['title']}\nLink: {item['href']}\nDescription: {item['body']}"
        for item in results
    )

@tool("search_images", description="Search for images based on a query.")
def search_images(query, num_images=5):
    debug_print(f"Searching for {num_images} images with query: {query}")
    send_tool_update(f"Searching for {num_images} images with query: {query}")
    results = serpapi_client.search({
        "engine": "google_images",
        "q": query,
    })

    images = results["images_results"][:num_images]

    clean_outputs = []

    for image in images:
        clean_outputs.append({
            "title": image["title"],
            "link": image["original"],
            "dimensions": f"{image['original_height']}x{image['original_width']}"
        })

    debug_print(f"Found {len(clean_outputs)} images for query: {query}")
    return clean_outputs

@tool("send_html_response", description="Send an HTML response to the user.", return_direct=True)
def send_html_response(html_content: str, height_guess: int = 720):
    debug_print(f"Sending HTML response to user: {html_content[:10]}\n\n...\n{html_content[-10:]}\n")
    send_HTML(html_content, height_guess)
    return "HTML response sent to user."
