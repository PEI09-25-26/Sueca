import json

import requests
from fastapi import APIRouter

from .. import state
from ..dto import RoundEndData, ScanEventDTO, StartGameRequest, StartGameResponse


router = APIRouter()


@router.post("/game/round_end")
async def round_end(data: RoundEndData):
    for game_id, ws in state.active_connections.items():
        try:
            message = {
                "type": "round_end",
                "round_number": data.round_number,
                "winner_team": data.winner_team,
                "winner_points": data.winner_points,
                "team1_points": data.team1_points,
                "team2_points": data.team2_points,
                "game_ended": data.game_ended,
            }
            await ws.send_text(json.dumps(message))
            print(f"[MIDDLEWARE] Round end notification sent to game {game_id}")
        except Exception as error:
            print(f"[MIDDLEWARE] Failed to send round end to {game_id}: {error}")

    return {"success": True}


@router.post("/game/new_round/{game_id}")
async def new_round(game_id: str):
    try:
        reset_message = {"action": "reset_cards"}
        if game_id in state.cv_connections:
            cv_ws = state.cv_connections[game_id]
            await cv_ws.send(json.dumps(reset_message))
            print(f"[MIDDLEWARE] CV reset command sent for game {game_id}")

        response = requests.post(f"{state.GAME_SERVICE_URL}/new_round", timeout=5)
        if response.status_code == 200:
            return {"success": True, "message": "Nova ronda iniciada"}
        return {"success": False, "message": "Erro ao iniciar nova ronda"}
    except Exception as error:
        print(f"[MIDDLEWARE] Error starting new round: {error}")
        return {"success": False, "message": str(error)}


@router.post("/game/start")
async def start_game(request: StartGameRequest):
    try:
        response = requests.post(
            f"{state.CV_SERVICE_URL}/cv/start",
            json={"game_id": request.roomId or "default"},
            timeout=5,
        )

        if response.status_code == 200:
            return StartGameResponse(
                success=True,
                message="Game started successfully",
                gameId=request.roomId or "default",
            )

        return StartGameResponse(
            success=False,
            message=f"Failed to start CV service: {response.text}",
            gameId="",
        )
    except requests.RequestException as error:
        print(f"[Middleware] Error starting CV service: {error}")
        return StartGameResponse(
            success=False,
            message=f"CV service unavailable: {str(error)}",
            gameId="",
        )


@router.post("/game/ready/{game_id}")
async def game_ready(game_id: str):
    if game_id in state.cv_connections:
        cv_ws = state.cv_connections[game_id]
        try:
            reset_command = json.dumps({"action": "reset_cards"})
            await cv_ws.send(reset_command)
            print(f"[Middleware] Game started for {game_id} - CV history reset")
            return {"success": True, "message": "Game started, ready for cards"}
        except Exception as error:
            print(f"[Middleware] Error resetting CV: {error}")
            return {"success": False, "message": str(error)}
    return {"success": False, "message": "Game not found"}


@router.post("/scan")
def receive_scan(event: ScanEventDTO):
    if not event.detection:
        return {
            "success": False,
            "message": "no card detected",
            "detection": event.detection.dict() if event.detection else None,
        }

    detection = state.CardDetection(
        rank=event.detection.rank,
        suit=event.detection.suit,
        confidence=event.detection.confidence,
    )

    backend_response = state.backend.send_card(detection)

    if backend_response is None:
        return {
            "success": False,
            "message": "backend unavailable",
            "detection": detection.to_json(),
        }

    return {
        "success": True,
        "message": "card forwarded",
        "backend_response": backend_response,
        "detection": detection.to_json(),
    }
