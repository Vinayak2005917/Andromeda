from pathlib import PurePosixPath

from config import settings
from supabase_client import create_server_supabase_client

ALLOWED_FILES = {"user.md", "notes.md", "logs.md"}


def memory_path(user_id: str, file_name: str) -> str:
    if file_name not in ALLOWED_FILES or PurePosixPath(file_name).name != file_name:
        raise ValueError("Invalid memory file")
    return f"{user_id}/{file_name}"


def list_memory(user_id: str) -> str:
    files = create_server_supabase_client().storage.from_(settings.memory_bucket).list(user_id)
    return "\n".join(str(item) for item in files)


def read_memory(user_id: str, file_name: str) -> str:
    path = memory_path(user_id, file_name)
    try:
        data = create_server_supabase_client().storage.from_(settings.memory_bucket).download(path)
        return data.decode("utf-8")
    except Exception as exc:
        if "not found" in str(exc).lower() or "404" in str(exc):
            return "File does not exist."
        raise


def append_memory(user_id: str, file_name: str, content: str) -> str:
    path = memory_path(user_id, file_name)
    current = read_memory(user_id, file_name)
    updated = f"{current}\n{content}\n" if current != "File does not exist." else f"{content}\n"
    create_server_supabase_client().storage.from_(settings.memory_bucket).upload(
        path, updated.encode("utf-8"), {"content-type": "text/markdown", "upsert": "true"}
    )
    return f"Updated '{file_name}'."
