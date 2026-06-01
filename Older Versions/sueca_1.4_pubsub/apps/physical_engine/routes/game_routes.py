from typing import Annotated

from fastapi import APIRouter, Query

from ..core.game_core import CardDTO, correct_last_card, get_state_data, process_card, reset_game_state, start_new_round
from ..event_publisher import publish_physical_event


router = APIRouter()


@router.get("/state")
def get_state(game_id: Annotated[str | None, Query()] = None):
    return get_state_data(game_id)


@router.get("/status")
def get_status(game_id: Annotated[str | None, Query()] = None):
    return get_state_data(game_id)


@router.post("/reset")
def reset_game(game_id: Annotated[str | None, Query()] = None, dealer_id: int = -1, starter_id: int = -1):
    result = reset_game_state(game_id, dealer_id, starter_id)
    publish_physical_event(game_id or 'default', 'physical_reset')
    return result


@router.post("/new_round")
def new_round(game_id: Annotated[str | None, Query()] = None):
    result = start_new_round(game_id)
    publish_physical_event(game_id or 'default', 'physical_new_round')
    return result


@router.post("/card")
def receive_card(card: CardDTO):
    result = process_card(card)
    card_payload = card.model_dump() if hasattr(card, 'model_dump') else card.dict()
    publish_physical_event(card.game_id or 'default', 'physical_card_received', card=card_payload)
    return result


@router.post("/card/correct")
def correct_card(card: CardDTO):
    result = correct_last_card(card)
    card_payload = card.model_dump() if hasattr(card, 'model_dump') else card.dict()
    publish_physical_event(card.game_id or 'default', 'physical_card_corrected', card=card_payload)
    return result
