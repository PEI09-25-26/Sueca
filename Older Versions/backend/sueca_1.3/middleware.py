from fastapi import FastAPI, Query
import requests
from fastapi import WebSocket
import json

app = FastAPI(title="Game Middleware", version="0.1")

GAME_SERVER_URL = "http://localhost:5000"

active_connections = []

@app.websocket("/ws/game")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)

    response = requests.get(f"{GAME_SERVER_URL}/api/status")
    await websocket.send_json({
        "type": "initial_state",
        "state": response.json()
    })

    try:
        while True:
            await websocket.receive_text()
    except:
        active_connections.remove(websocket)

@app.post("/game/event")
async def receive_event(event: dict):
    disconnected = []

    for ws in active_connections:
        try:
            await ws.send_json(event)
        except:
            disconnected.append(ws)

    for ws in disconnected:
        active_connections.remove(ws)

    return {"ok": True}

@app.get("/game/status")
def get_status(game_id: str | None = Query(default=None)):
    params = {"game_id": game_id} if game_id else None
    response = requests.get(f"{GAME_SERVER_URL}/api/status", params=params)
    return response.json()


@app.post("/game/join")
def join_game(payload: dict):
    response = requests.post(
        f"{GAME_SERVER_URL}/api/join",
        json=payload
    )
    return response.json()


@app.post("/game/cut_deck")
def cut_deck(payload: dict):
    response = requests.post(
        f"{GAME_SERVER_URL}/api/cut_deck",
        json=payload
    )
    return response.json()


@app.post("/game/select_trump")
def select_trump(payload: dict):
    response = requests.post(
        f"{GAME_SERVER_URL}/api/select_trump",
        json=payload
    )
    return response.json()


@app.post("/game/play")
def play_card(payload: dict):
    response = requests.post(
        f"{GAME_SERVER_URL}/api/play",
        json=payload
    )
    return response.json()


@app.post("/game/the_council_has_decided_your_fate")
def the_council_has_decided_your_fate(payload: dict):
    response = requests.post(
        f"{GAME_SERVER_URL}/api/the_council_has_decided_your_fate",
        json=payload
    )
    return response.json()


@app.get("/game/hand/{player_name}")
def get_hand(player_name: str, game_id: str | None = Query(default=None)):
    params = {"game_id": game_id} if game_id else None
    response = requests.get(
        f"{GAME_SERVER_URL}/api/hand/{player_name}",
        params=params,
    )
    return response.json()


@app.post("/game/reset")
def reset_game():
    response = requests.post(f"{GAME_SERVER_URL}/api/reset")
    return response.json()

