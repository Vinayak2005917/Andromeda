import os
from datetime import datetime
import asyncio
import requests
import requests
from ddgs import DDGS
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI

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

OpenAI_GPT5_Nano = ChatOpenAI(
    model="openai/gpt-5-nano",
    base_url="https://api.aicredits.in/v1",
    api_key=api_key,
)


@tool("update_user", description="Update the user about the progress you have made so far on the task you are working on. the 2nd parameter is a boolean flag indicating whether the research is complete or not.")
def update_user(content: str, research_flag: bool = False):
    debug_print(f"Sending update to user: {content} with research_flag={research_flag}")
    send_user_update(f"Update: {content}", research_flag)
    return f"Update sent to user: {content} with research_flag={research_flag}"


async def read_webpage(url: str, query: str):
    debug_print(f"Reading webpage {url[:100]}")
    send_tool_update(f"Reading webpage {url[:40]}")
    response = await asyncio.to_thread(requests.get,f"https://r.jina.ai/{url}",timeout=30)
    summarized_response = await OpenAI_GPT5_Nano.ainvoke(f"Summarize the information relevant to this question: Question: {query} Webpage content: {response.text}")
    return summarized_response.content[:6000]

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

@tool("batch_read_pages", description="Read a batch webpages of {'url':'query', 'url':'query'}, never more than 5")
async def batch_read_pages(pages: dict[str, str]):
    pages = dict(list(pages.items())[:5])

    debug_print(f"Batch reading {len(pages)} webpages")
    send_tool_update(f"Reading {len(pages)} webpages concurrently")

    tasks = [read_webpage(url, query) for url, query in pages.items()]

    results = await asyncio.gather(*tasks,return_exceptions=True)

    # Preserve URL + summary so the agent knows which result came from where
    output = []

    for (url, query), result in zip(pages.items(), results):
        if isinstance(result, Exception):
            debug_print(f"Failed reading {url}: {result}")
            output.append(f"URL: {url}\n ERROR: Could not read this webpage.\n")
        else:
            output.append(f"URL: {url}\n Relevant to: {query}\n\n {result}")
    return "\n\n--- NEXT WEBPAGE ---\n\n".join(output)

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
