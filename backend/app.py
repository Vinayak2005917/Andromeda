import asyncio

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agent import ask_agent
from auth import extract_user_data, get_current_user, verify_access_token
from auth_routes import router as auth_router
from config import settings
from websocket import manager

app = FastAPI(title="Andromeda Backend")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)


@app.get("/api/v1/auth/me")
def get_me(user=Depends(get_current_user)):
    return extract_user_data(user)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    access_token = websocket.cookies.get("access_token")

    if not access_token:
        await websocket.close(code=1008)
        return

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

            response = await asyncio.to_thread(ask_agent,user_input)

            await manager.send(websocket,{
                    "type": "response",
                    "content": response,
                    "user_id": str(user.id),
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
