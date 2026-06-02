from fastapi import APIRouter
from typing import Optional

try:
    from ..core.game_core import CardDTO, get_state_data, process_card, reset_game_state, start_new_round, undo_last_play, correct_last_card, ensure_game_ready
    from ..event_publisher import publish_physical_event
except (ImportError, ValueError):
    from apps.physical_engine.core.game_core import CardDTO, get_state_data, process_card, reset_game_state, start_new_round, undo_last_play, correct_last_card, ensure_game_ready
    from apps.physical_engine.event_publisher import publish_physical_event


router = APIRouter()


@router.get("/state")
def get_state(game_id: Optional[str] = None):
    return get_state_data(game_id)


@router.post("/reset")
def reset_game(game_id: Optional[str] = None, dealer_id: int = -1, starter_id: int = -1):
    result = reset_game_state(game_id, dealer_id, starter_id)
    publish_physical_event(game_id or 'default', 'physical_reset')
    return result


@router.post("/ready")
def game_ready(game_id: Optional[str] = None, dealer_id: int = -1, starter_id: int = -1):
    """Ensure game is ready for play without wiping setup data if already present."""
    return ensure_game_ready(game_id, dealer_id, starter_id)


@router.post("/new_round")
def new_round(game_id: Optional[str] = None):
    result = start_new_round(game_id)
    publish_physical_event(game_id or 'default', 'physical_new_round')
    return result


@router.post("/card")
def receive_card(card: CardDTO):
    result = process_card(card)
    card_payload = card.model_dump() if hasattr(card, 'model_dump') else card.dict()
    publish_physical_event(card.game_id or 'default', 'physical_card_received', card=card_payload)
    return result


@router.post("/correct")
def correct_card(card: CardDTO):
    result = correct_last_card(card)
    card_payload = card.model_dump() if hasattr(card, 'model_dump') else card.dict()
    publish_physical_event(card.game_id or 'default', 'physical_card_corrected', card=card_payload)
    return result


@router.post("/play/undo")
def undo_play(game_id: Optional[str] = None):
    result = undo_last_play(game_id)
    publish_physical_event(game_id or 'default', 'physical_play_undone', undone_player=result.get("undone_player"))
    return result
