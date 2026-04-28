import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../packages/types/python"))

from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv

from ws_handler import handle_websocket

load_dotenv()

app = FastAPI(title="PairCooking API")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await handle_websocket(websocket)
