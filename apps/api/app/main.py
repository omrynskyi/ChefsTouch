from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv

from apps.api.app.ws_handler import handle_websocket

load_dotenv()

app = FastAPI(title="PairCooking API")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await handle_websocket(websocket)
