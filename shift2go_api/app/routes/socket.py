from app.db import models
from app.db.session import get_db
from fastapi import  WebSocket, APIRouter, status, Depends, Query, Cookie
import typing as t

from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect


socket_router = r = APIRouter()




html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


class ConnectionManager:
    def __init__(self):
        self.active_connections: t.List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


# @r.get("/")
# async def get():
#     return HTMLResponse(html)


async def get_cookie_or_token(
    websocket: WebSocket,
    session: t.Optional[str] = Cookie(None),
    token: t.Optional[str] = Query(None),
):
    # if session is None and token is None:
    #     await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return session or token


@r.websocket("/web_socket")
async def websocket_endpoint(
    websocket: WebSocket, 
    client_id: int,
    # cookie_or_token: str = Depends(get_cookie_or_token),
    db=Depends(get_db)
):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Client #{client_id} says: {data}")
            for user in db.query(models.User).all():
                await manager.send_personal_message(f"You wrote: {user.email}", websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")