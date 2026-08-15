from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from supabase_client import create_server_supabase_client


def _client():
    return create_server_supabase_client()


def list_conversations(user_id: str) -> list[dict]:
    response = (
        _client().table("conversations")
        .select("id,title,thread_id,created_at,updated_at")
        .eq("user_id", user_id).order("updated_at", desc=True).execute()
    )
    return response.data or []


def delete_empty_conversations(user_id: str) -> None:
    """Remove conversation rows whose agent thread has no user/assistant messages."""
    from agent import thread_has_messages

    for conversation in list_conversations(user_id):
        if not thread_has_messages(conversation["thread_id"]):
            delete_conversation(user_id, conversation["id"])


def create_conversation(user_id: str, title: str = "New conversation") -> dict:
    conversation_id = str(uuid4())
    response = _client().table("conversations").insert({
        "id": conversation_id,
        "user_id": user_id,
        "title": title.strip()[:120] or "New conversation",
        "thread_id": conversation_id,
    }).execute()
    return response.data[0]


def get_owned_conversation(user_id: str, conversation_id: str) -> dict:
    response = (
        _client().table("conversations")
        .select("id,title,thread_id,created_at,updated_at")
        .eq("id", conversation_id).eq("user_id", user_id)
        .maybe_single().execute()
    )
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return response.data


def rename_conversation(user_id: str, conversation_id: str, title: str) -> dict:
    get_owned_conversation(user_id, conversation_id)
    response = (_client().table("conversations").update({
        "title": title.strip()[:120] or "New conversation",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", conversation_id).eq("user_id", user_id).execute())
    return response.data[0]


def touch_conversation(user_id: str, conversation_id: str) -> None:
    _client().table("conversations").update({
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", conversation_id).eq("user_id", user_id).execute()


def delete_conversation(user_id: str, conversation_id: str) -> None:
    get_owned_conversation(user_id, conversation_id)
    _client().table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()
