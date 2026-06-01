import json
import asyncio

from fastapi import APIRouter, Query

from .. import state
from ..dto import RoundEndData, ScanEventDTO, StartGameRequest, StartGameResponse, CorrectCardRequest


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

        response = await asyncio.to_thread(
            state.INTERNAL_HTTP.post,
            f"{state.GAME_SERVICE_URL}/new_round",
            timeout=5,
        )
        if response.status_code == 200:
            return {"success": True, "message": "Nova ronda iniciada"}
        return {"success": False, "message": "Erro ao iniciar nova ronda"}
    except Exception as error:
        print(f"[MIDDLEWARE] Error starting new round: {error}")
        return {"success": False, "message": str(error)}


@router.post("/game/start")
async def start_game(request: StartGameRequest):
    try:
        response = await asyncio.to_thread(
            state.INTERNAL_HTTP.post,
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
    except Exception as error:
        print(f"[Middleware] Error starting CV service: {error}")
        return StartGameResponse(
            success=False,
            message=f"CV service unavailable: {str(error)}",
            gameId="",
        )


@router.post("/game/ready/{game_id}")
async def game_ready(game_id: str, dealer_id: int = Query(-1), starter_id: int = Query(-1)):
    try:
        # Reset CV history for this game and RESUME in TRICK mode
        if game_id in state.cv_connections:
            cv_ws = state.cv_connections[game_id]

            # Switch mode to trick and resume
            await cv_ws.send(json.dumps({"action": "set_mode", "mode": "trick"}))

            # action=resume or reset with resume=True
            reset_command = json.dumps({"action": "reset_cards", "full": True, "resume": True})
            await cv_ws.send(reset_command)
            print(f"[Middleware] CV history reset and RESUMED in TRICK mode for {game_id}")

        # Ensure Physical Engine is ready for this game
        response = await asyncio.to_thread(
            state.INTERNAL_HTTP.post,
            f"{state.GAME_SERVICE_URL}/ready",
            params={"game_id": game_id, "dealer_id": dealer_id, "starter_id": starter_id},
            timeout=5,
        )
        
        if response.status_code == 200:
            return StartGameResponse(
                success=True,
                message="Game reset and ready",
                gameId=game_id,
                gameState=response.json().get("game_state")
            )
        return StartGameResponse(
            success=False,
            message=f"Failed to reset game engine: {response.text}",
            gameId=game_id
        )
    except Exception as error:
        print(f"[Middleware] Error in game_ready: {error}")
        return StartGameResponse(success=False, message=str(error), gameId=game_id)


@router.post("/game/correct/{game_id}")
async def correct_game_card(game_id: str, request: CorrectCardRequest):
    try:
        # 1. Forward correction to Physical Engine
        response = await asyncio.to_thread(
            state.INTERNAL_HTTP.post,
            f"{state.GAME_SERVICE_URL}/correct",
            json={
                "game_id": game_id,
                "rank": request.rank,
                "suit": request.suit,
            },
            timeout=5,
        )
        
        if response.status_code == 200:
            # 2. Forward correction to CV service if wrong_label is provided
            if request.wrong_label and game_id in state.cv_connections:
                # Note: Currently CV expects rank/suit in /cv/undo, 
                # but we can implement a custom command or just rely on the engine sync.
                pass
            return response.json()
        
        return {"success": False, "message": f"Engine error: {response.text}"}
    except Exception as error:
        print(f"[Middleware] Error correcting card: {error}")
        return {"success": False, "message": str(error)}


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
