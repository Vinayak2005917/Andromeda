import asyncio

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from agent import ask_agent, get_thread_messages
from auth import extract_user_data, get_current_user, verify_access_token
from auth_routes import router as auth_router
from config import settings
from conversations import create_conversation, delete_conversation, delete_empty_conversations, get_owned_conversation, list_conversations, rename_conversation, touch_conversation
from schemas import ConversationCreateRequest, ConversationRenameRequest
from websocket import manager, reset_active_connection, set_active_connection

app = FastAPI(title="Andromeda Backend")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




app.include_router(auth_router)


@app.get("/api/v1/conversations")
def get_conversations(user=Depends(get_current_user)):
    user_id = str(user.id)
    delete_empty_conversations(user_id)
    return list_conversations(user_id)


@app.post("/api/v1/conversations", status_code=status.HTTP_201_CREATED)
def post_conversation(payload: ConversationCreateRequest, user=Depends(get_current_user)):
    return create_conversation(str(user.id), payload.title)


@app.patch("/api/v1/conversations/{conversation_id}")
def patch_conversation(conversation_id: str, payload: ConversationRenameRequest, user=Depends(get_current_user)):
    return rename_conversation(str(user.id), conversation_id, payload.title)


@app.get("/api/v1/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, user=Depends(get_current_user)):
    conversation = get_owned_conversation(str(user.id), conversation_id)
    return get_thread_messages(conversation["thread_id"])


@app.delete("/api/v1/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_conversation(conversation_id: str, user=Depends(get_current_user)):
    delete_conversation(str(user.id), conversation_id)


@app.get("/api/v1/auth/me")
def get_me(user=Depends(get_current_user)):
    return extract_user_data(user)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    access_token = websocket.cookies.get("access_token")

    user = None
    if access_token:
        try:
            user = verify_access_token(access_token)
        except Exception:
            await websocket.close(code=1008)
            return

    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") != "message":
                continue

            user_input = data.get("content", "").strip()

            if not user_input:
                continue

            user_id = str(user.id) if user else None
            conversation_id = data.get("conversation_id")
            if user:
                if not conversation_id:
                    await manager.send(websocket, {"type": "error", "content": "Select a conversation first."})
                    continue
                try:
                    conversation = get_owned_conversation(user_id, conversation_id)
                except Exception as exc:
                    await manager.send(websocket, {"type": "error", "content": getattr(exc, "detail", "Conversation not found")})
                    continue
                thread_id = conversation["thread_id"]
                touch_conversation(user_id, conversation_id)
            else:
                thread_id = data.get("guest_thread_id", "")
                if not thread_id.startswith("guest:") or len(thread_id) > 80:
                    await manager.send(websocket, {"type": "error", "content": "Invalid guest session."})
                    continue

            connection_token = set_active_connection(websocket)
            try:
                response = await asyncio.to_thread(ask_agent, user_id, thread_id, user_input)
            finally:
                reset_active_connection(connection_token)

            await manager.send(websocket,{
                    "type": "response",
                    "content": response,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                },
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/health")
@app.head("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)
