import asyncio
import inspect
from datetime import datetime
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

        if self.loop is None:
            self.loop = asyncio.get_running_loop()

        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def send(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for websocket in self.connections.copy():
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(websocket)


manager = ConnectionManager()


def send_tool_update(contents: str):
    if manager.loop is None:
        return
    
    frame = inspect.currentframe().f_back
    file_name = frame.f_globals.get("__file__", "unknown")
    file_name = file_name.split("/")[-1].split("\\")[-1]
    function_name = frame.f_code.co_name

    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S.%f")[:-3]

    message = {
        "type": "tool_update",
        "timestamp": timestamp,
        "file": file_name,
        "function": function_name,
        "content": contents,
    }

    # Safely schedule the async WebSocket send
    asyncio.run_coroutine_threadsafe(manager.broadcast(message),manager.loop)