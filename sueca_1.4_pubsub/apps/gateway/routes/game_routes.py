import json
import asyncio
import uuid

from fastapi import APIRouter, Depends
import logging

from .. import state
from ..helpers import require_any_token
from apps.virtual_engine.session import session_manager
logger = logging.getLogger(__name__)
from ..dto import CorrectCardRequest, RoundEndData, ScanEventDTO, StartGameRequest, StartGameResponse


router = APIRouter()
INTERNAL_ERROR_MESSAGE = "internal error"


def _suit_symbol_to_suffix(suit: str) -> str:
    normalized = suit.strip()
    if normalized in {"♣", "clubs", "Club", "club", "Clubs"}:
        return "c"
    if normalized in {"♦", "diamonds", "Diamond", "diamond", "Diamonds"}:
        return "d"
    if normalized in {"♥", "hearts", "Heart", "heart", "Hearts"}:
        return "h"
    if normalized in {"♠", "spades", "Spade", "spade", "Spades"}:
        return "s"
    return normalized[-1:].lower()


@router.post("/game/round_end", dependencies=[Depends(require_any_token)])
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
        except Exception:
            logger.exception("Failed to send round end to %s", game_id)

    return {"success": True}


@router.post("/game/new_round/{game_id}", dependencies=[Depends(require_any_token)])
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
        return {"success": False, "message": INTERNAL_ERROR_MESSAGE}
    except Exception:
        logger.exception("Error starting new round for %s", game_id)
        return {"success": False, "message": INTERNAL_ERROR_MESSAGE}


@router.post("/game/start")
async def start_game(request: StartGameRequest, payload = Depends(require_any_token)):
    # Always generate a unique game_id for new physical sessions if not provided
    game_id = request.roomId or f"phys_{uuid.uuid4().hex[:8]}"
    try:
        # 1. Start CV service
        response = await asyncio.to_thread(
            state.INTERNAL_HTTP.post,
            f"{state.CV_SERVICE_URL}/cv/start",
            json={"game_id": game_id},
            timeout=5,
        )

        if response.status_code == 200:
            # 2. Reset the referee state for this specific game_id and dealer
            dealer_id = request.dealerId if request.dealerId is not None else 1 # Default North
            
            await asyncio.to_thread(
                state.INTERNAL_HTTP.post,
                f"{state.GAME_SERVICE_URL}/reset",
                params={"game_id": game_id, "dealer_id": dealer_id},
                timeout=2
            )

            token = None
            # Use uid if logged in, otherwise generate a guest player_id
            is_guest = not payload.get("uid")
            player_id = payload.get("uid") or f"guest_{uuid.uuid4().hex[:8]}"
            player_name = request.playerName or payload.get("username") or "Host"
            
            # Always issue a session token for physical game management
            token = session_manager.create_session(game_id, player_id, player_name)
            logger.info("Started NEW physical game id=%s for %s", game_id, "guest" if is_guest else "user")

            return StartGameResponse(
                success=True,
                message="Game started successfully",
                gameId=game_id,
                token=token
            )

        logger.warning("Failed to start CV service: %s", response.text)
        return StartGameResponse(
            success=False,
            message="failed to start CV service",
            gameId="",
        )
    except Exception:
        logger.exception("Error starting CV service for request: %s", request)
        return StartGameResponse(
            success=False,
            message="CV service unavailable",
            gameId="",
        )


@router.post("/game/ready/{game_id}", dependencies=[Depends(require_any_token)])
async def game_ready(game_id: str, dealer_id: int | None = None, starter_id: int | None = None):
    if game_id in state.cv_connections:
        cv_ws = state.cv_connections[game_id]
        try:
            # Sync dealer and/or starter if provided
            game_state = None
            if dealer_id is not None or starter_id is not None:
                params = {"game_id": game_id}
                if dealer_id is not None: params["dealer_id"] = dealer_id
                if starter_id is not None: params["starter_id"] = starter_id
                
                response = await asyncio.to_thread(
                    state.INTERNAL_HTTP.post,
                    f"{state.GAME_SERVICE_URL}/reset",
                    params=params,
                    timeout=2
                )
                if response.status_code == 200:
                    game_state = response.json().get("game_state")

            reset_command = json.dumps({"action": "reset_cards"})
            await cv_ws.send(reset_command)
            print(f"[Middleware] Game started for {game_id} - CV history reset")
            
            # Notify mobile client that game is ready for next player
            if game_id in state.active_connections:
                mobile_ws = state.active_connections[game_id]
                try:
                    await mobile_ws.send_json({
                        "success": True,
                        "message": "game_ready",
                        "status": "Ready for next player's card",
                        "game_state": game_state
                    })
                    print(f"[Middleware] Notified mobile client for {game_id}: game ready")
                except Exception as e:
                    print(f"[Middleware] Failed to notify mobile: {e}")
            
            return {"success": True, "message": "Game started, ready for cards", "game_state": game_state}
        except Exception:
            logger.exception("Error resetting CV for %s", game_id)
            return {"success": False, "message": INTERNAL_ERROR_MESSAGE}
    return {"success": False, "message": "Game not found"}


@router.post("/game/correct/{game_id}", dependencies=[Depends(require_any_token)])
async def correct_card(game_id: str, request: CorrectCardRequest):
    try:
        if game_id in state.cv_connections and request.wrong_label:
            cv_ws = state.cv_connections[game_id]
            await cv_ws.send(json.dumps({
                "action": "correct_card",
                "wrong_label": request.wrong_label,
                "correct_label": f"{request.rank}{_suit_symbol_to_suffix(request.suit)}",
            }))
            print(f"[Middleware] CV correction sent for game {game_id}")

        response = await asyncio.to_thread(
            state.INTERNAL_HTTP.post,
            f"{state.GAME_SERVICE_URL}/card/correct",
            json={
                "rank": request.rank,
                "suit": request.suit,
                "game_id": game_id,
            },
            timeout=5,
        )

        if response.status_code == 200:
            payload = response.json()
            if game_id in state.active_connections:
                mobile_ws = state.active_connections[game_id]
                try:
                    await mobile_ws.send_json({
                        "success": True,
                        "message": "card_corrected",
                        "game_state": payload,
                    })
                except Exception:
                    logger.exception("Failed to notify mobile of correction for %s", game_id)
            return {"success": True, "message": "Carta corrigida", "backend_response": payload}

        logger.warning("Failed to correct card for %s: %s", game_id, response.text)
        return {"success": False, "message": "Erro ao corrigir carta"}
    except Exception:
        logger.exception("Error correcting card for %s", game_id)
        return {"success": False, "message": INTERNAL_ERROR_MESSAGE}


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
