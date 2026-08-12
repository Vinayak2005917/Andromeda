import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from websocket import manager
from agent import ask_agent

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "message":
                user_input = data["content"]
                response = await asyncio.to_thread(ask_agent, user_input)
                await manager.send(websocket, {"type": "response", "content": response})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


#health endpoint
@app.get("/health")
@app.head("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
