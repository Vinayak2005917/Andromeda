import os
from datetime import datetime
from langchain_openai import ChatOpenAI
import requests
import shutil
from langchain.tools import tool
now = datetime.now()
from utils import *
from ddgs import DDGS
date_time_info = now.strftime("%H:%M:%S on %Y-%m-%d")
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")

@tool("check_date_time", description="Check the current date and time.")
def check_date_time():
    now = datetime.now()
    date_time_info = now.strftime("%H:%M:%S on %Y-%m-%d")
    return f"The current date and time is: {date_time_info}"

@tool("read_directory", description="Read the contents of all files in the memory directory.")
def read_directory(reason: str):
    directory_path = "./memory"
    debug_print(f"Reading directory")
    output = []
    try:
        for item in sorted(os.listdir(directory_path)):
            item_path = os.path.join(directory_path, item)
            output.append(
                {
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "extension": "" if os.path.isdir(item_path) else os.path.splitext(item)[1],
                    "size": os.path.getsize(item_path),
                    "path": os.path.relpath(item_path, "./memory")
                }
            )
        output = "\n".join(str(item) for item in output)
        return output
    except Exception as e:
        debug_print(f"Error reading directory {directory_path}: {e}")
        return str(e)

@tool("Read_file",description="Read the contents of a file.")
def read_file(file_name: str):
    file_path = "./memory/" + file_name
    debug_print(f"Reading file {file_path}")

    try:
        if not os.path.exists(file_path):
            debug_print(f"File {file_path} does not exist.")
            return "File does not exist."
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        debug_print(f"Error reading file {file_path}: {e}")
        return str(e)

@tool("write_to_file", description="Append content to an existing file.")
def write_to_file(file_name: str, content: str) -> str:
    file_path = "./memory/" + file_name
    if not os.path.exists(file_path):
        return "File does not exist."
    debug_print(f"Appending to {file_path}")
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content)
        debug_print(f"Appended content to {file_path}")
        return f"Updated '{file_name}'."
    except Exception as e:
        debug_print(f"Error appending to file {file_path}: {e}")
        return str(e)


OpenAI_GPT5_Nano = ChatOpenAI(
    model="openai/gpt-5-nano",
    base_url="https://api.aicredits.in/v1",
    api_key=os.getenv("OPENAI_API_KEY")
)

def summarize_for_query(query, webpage_text):

    system_prompt = f"""
    You are an information extraction system.

    USER QUESTION:
    {query}

    WEBPAGE:
    {webpage_text}

    TASK:
    Extract ONLY information that directly helps answer the user's question.

    IMPORTANT:
    - Do NOT summarize the whole article
    - Do NOT explain background information
    - Do NOT include unrelated technical details
    - Ignore introductions and general context
    - Ignore webpage navigation/UI/ads

    Return:
    - Only directly relevant facts
    - Short bullet points
    - Exact reasons, dates, numbers, events if present
    """

    debug_print(f"Summarizing webpage for query: {query}")
    response = OpenAI_GPT5_Nano.invoke(system_prompt)

    return response.content

@tool("Read_webpage",description="Read and summarize a webpage based on the user's query. Returns only the most relevant information from the page.")
def read_webpage(url: str, query: str):

    debug_print(f"reading page {url} for query: {query}")

    reader_url = f"https://r.jina.ai/{url}"

    response = requests.get(reader_url)

    response_text = summarize_for_query(query, response.text)

    debug_print(f"returning read webpage response: {response_text[:50]}...")

    return response_text[:6000]

@tool(
    "Get_relevant_webpages",
    description="""
    Search the web for relevant webpages.

    IMPORTANT:
    This tool only gives titles and URLs.
    You MUST use Read_webpage afterward
    to actually read the contents.
    """
)
def Get_relevant_webpages(query: str):

    debug_print(f"Performing web search for query: {query}")

    results = DDGS().text(query,max_results=5)

    formatted = []

    for r in results:
        formatted.append(
            f"Title: {r['title']}\n"
            f"Link: {r['href']}\n"
            f"Description: {r['body']}\n"
        )
    debug_print(f"Returning {len(formatted)} relevant webpages for query: {query}")

    return "\n\n".join(formatted)