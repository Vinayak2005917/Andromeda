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
                # Keep the event loop free so tool_update frames can stream
                # to the client while the synchronous agent is working.
                response = await asyncio.to_thread(ask_agent, user_input)
                await manager.send(websocket, {"type": "response", "content": response})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8025)
