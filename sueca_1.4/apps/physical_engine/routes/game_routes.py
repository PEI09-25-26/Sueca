from fastapi import APIRouter

try:
    from ..core.game_core import CardDTO, get_state_data, process_card, reset_game_state, start_new_round
except ImportError:
    from core.game_core import CardDTO, get_state_data, process_card, reset_game_state, start_new_round


router = APIRouter()


@router.get("/state")
def get_state():
    return get_state_data()


@router.post("/reset")
def reset_game():
    return reset_game_state()


@router.post("/new_round")
def new_round():
    return start_new_round()


@router.post("/card")
def receive_card(card: CardDTO):
    return process_card(card)
