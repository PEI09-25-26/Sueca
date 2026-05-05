from fastapi import APIRouter

try:
    from ..core.game_core import CardDTO, get_state_data, process_card, reset_game_state, start_new_round
    from ..event_publisher import publish_physical_event
except ImportError:
    from ..core.game_core import CardDTO, get_state_data, process_card, reset_game_state, start_new_round
    from ..event_publisher import publish_physical_event


router = APIRouter()


@router.get("/state")
def get_state():
    return get_state_data()


@router.post("/reset")
def reset_game():
    result = reset_game_state()
    publish_physical_event('default', 'physical_reset')
    return result


@router.post("/new_round")
def new_round():
    result = start_new_round()
    publish_physical_event('default', 'physical_new_round')
    return result


@router.post("/card")
def receive_card(card: CardDTO):
    result = process_card(card)
    card_payload = card.model_dump() if hasattr(card, 'model_dump') else card.dict()
    publish_physical_event('default', 'physical_card_received', card=card_payload)
    return result
