from typing import Optional
import requests
from pydantic import BaseModel
import threading
import time
import copy

try:
    from ..card_mapper import CardMapper
    from ..referee import Referee
except ImportError:
    # Fallback for direct script execution outside package context.
    from card_mapper import CardMapper
    from referee import Referee

from shared.config import SERVICES


state_sync_lock = threading.Lock()
GAME_SESSIONS: dict[str, Referee] = {"default": Referee(game_id="default")}
PRE_ROUND_SESSIONS: dict[str, Referee] = {}
REF_HISTORY: dict[str, list[tuple[Referee, dict]]] = {}

MIDDLEWARE_URL = f"{SERVICES.gateway_url}/game/physical/state"
MIDDLEWARE_ROUND_END_URL = f"{SERVICES.gateway_url}/game/round_end"
CV_UNDO_URL = f"{SERVICES.cv_service_url}/cv/undo"

# Game constants
MAX_ROUNDS = 4
MAX_RODADAS = 10


class CardDTO(BaseModel):
    rank: str
    suit: str
    confidence: Optional[float] = None
    game_id: Optional[str] = None


def _normalize_game_id(game_id: Optional[str]) -> str:
    normalized_game_id = (game_id or "default").strip()
    return normalized_game_id or "default"


def _get_ref(game_id: Optional[str] = None) -> Referee:
    normalized_game_id = _normalize_game_id(game_id)
    game_ref = GAME_SESSIONS.get(normalized_game_id)
    if game_ref is None:
        game_ref = Referee(game_id=normalized_game_id)
        GAME_SESSIONS[normalized_game_id] = game_ref
    return game_ref


def _snapshot_card(card: CardDTO) -> dict:
    payload = card.model_dump() if hasattr(card, "model_dump") else card.dict()
    return {
        "rank": payload.get("rank"),
        "suit": payload.get("suit"),
        "confidence": payload.get("confidence"),
        "game_id": payload.get("game_id"),
    }


def get_state_data(game_id: Optional[str] = None):
    return _get_ref(game_id).state()


def _send_state_to_middleware(game_id: Optional[str] = None):
    with state_sync_lock:
        time.sleep(0.05)
        try:
            state_payload = _get_ref(game_id).state()
            requests.post(MIDDLEWARE_URL, json=state_payload, timeout=1.0)
            print("[SYNC] State pushed to middleware")
        except requests.exceptions.RequestException as error:
            print(f"[WARN] State sync failed: {error}")


def _push_state(game_id: Optional[str] = None):
    threading.Thread(target=_send_state_to_middleware, args=(game_id,), daemon=True).start()


def _card_to_id(card: CardDTO) -> Optional[int]:
    try:
        rank_index = CardMapper.RANKS.index(card.rank)
        suit_index = CardMapper.SUITS.index(card.suit)
        return suit_index * CardMapper.SUITSIZE + rank_index
    except ValueError:
        print("[DEBUG] Invalid card!")
        return None


def reset_game_state(game_id: Optional[str] = None, dealer_id: int = -1, starter_id: int = -1):
    normalized_game_id = _normalize_game_id(game_id)
    ref = Referee(game_id=normalized_game_id)
    
    # Default dealer to 0 (East) if not specified
    if dealer_id == -1:
        dealer_id = 0
    ref.dealer = dealer_id

    if starter_id != -1:
        ref.current_player = starter_id
    else:
        ref.current_player = (dealer_id + 1) % 4

    ref.phase = "waiting"
    GAME_SESSIONS[normalized_game_id] = ref
    PRE_ROUND_SESSIONS.pop(normalized_game_id, None)
    REF_HISTORY.pop(normalized_game_id, None)
    return {
        "success": True,
        "message": "Game reset",
        "dealer": dealer_id,
        "starter": ref.current_player,
        "game_state": ref.state(),
    }


def ensure_game_ready(game_id: Optional[str] = None, dealer_id: int = -1, starter_id: int = -1):
    normalized_game_id = _normalize_game_id(game_id)
    ref = _get_ref(normalized_game_id)

    if ref.trump_set:
        print(f"[DEBUG] Game {normalized_game_id} already has trump. Updating dealer/starter only.")
        if dealer_id != -1:
            ref.dealer = dealer_id
        if starter_id != -1:
            ref.current_player = starter_id

        return {
            "success": True,
            "message": "Game state preserved",
            "dealer": ref.dealer,
            "starter": ref.current_player,
            "game_state": ref.state(),
        }

    return reset_game_state(game_id, dealer_id, starter_id)


def start_new_round(game_id: Optional[str] = None):
    game_ref = _get_ref(game_id)
    team1_vict = game_ref.team1_victories
    team2_vict = game_ref.team2_victories
    old_match = game_ref.current_match
    
    new_ref = Referee(game_id=game_ref.game_id)
    new_ref.team1_victories = team1_vict
    new_ref.team2_victories = team2_vict
    new_ref.dealer = (game_ref.dealer + 1) % 4
    new_ref.current_player = (new_ref.dealer + 1) % 4
    new_ref.current_match = old_match + 1
    
    GAME_SESSIONS[game_ref.game_id] = new_ref
    PRE_ROUND_SESSIONS.pop(game_ref.game_id, None)
    REF_HISTORY.pop(game_ref.game_id, None)
    return {
        "success": True,
        "message": f"Nova ronda {new_ref.current_round} iniciada",
        "round": new_ref.current_round,
        "game_state": new_ref.state(),
    }


def process_card(card: CardDTO):
    game_id = _normalize_game_id(card.game_id)
    ref = _get_ref(game_id)

    who_played = ref.current_player

    print(f"[DEBUG] Received card: {card.rank} {card.suit} from player {who_played}")
    card_id = _card_to_id(card)
    if card_id is None:
        return {"success": False, "message": "Invalid card"}

    REF_HISTORY.setdefault(game_id, []).append((copy.deepcopy(ref), _snapshot_card(card)))

    if ref.trump_set and ref.trick_starter is None and len(ref.card_queue) == 0:
        ref.trick_starter = ref.current_player

    ref.inject_card(card_id)
    print(f"[DEBUG] Card injected. Queue size: {len(ref.card_queue)}")

    if not ref.trump_set:
        print(f"[DEBUG] Setting trump for dealer {ref.dealer}...")
        ref.set_trump()
        _push_state(game_id)
        res = ref.state()
        res.update({
            "success": True,
            "message": "Trump card set",
            "who_played": str(ref.dealer),
            "next_player": str(ref.current_player),
            "card": card.rank + card.suit,
        })
        return res

    next_player = (who_played + 1) % 4
    ref.current_player = next_player

    if len(ref.card_queue) >= 4:
        print("[DEBUG] Enough cards for a round, playing round...")
        PRE_ROUND_SESSIONS[game_id] = copy.deepcopy(ref)

        round_ok = ref.play_round()
        print(f"[REFEREE] Round played. Team 1 points: {ref.team1_points}, Team 2 points: {ref.team2_points}")

        round_ended = False
        winner_team = None
        winner_points = 0

        if not round_ok:
            round_ended = True
            if ref.team1_victories > ref.team2_victories:
                winner_team = 1
                winner_points = ref.team1_victories
            else:
                winner_team = 2
                winner_points = ref.team2_victories
            print(f"[RONDA] Acabou por rendicao! Equipa {winner_team} ganhou com {winner_points} pontos")
        elif ref.rounds_played >= MAX_RODADAS:
            round_ended = True
            
            # Capture match details before calling get_game_winner which might reset points if called there (though we removed it)
            # Actually we removed self.reset_players() from get_game_winner(), so points are safe.
            
            ref.get_game_winner() # Update victories
            
            if ref.team1_points > ref.team2_points:
                winner_team = 1
                winner_points = ref.team1_points
            else:
                winner_team = 2
                winner_points = ref.team2_points
            print(f"[RONDA] Acabou apos 10 rodadas! Equipa {winner_team} ganhou com {winner_points} pontos")

        if round_ended:
            def _notify_round_end(data: dict):
                try:
                    requests.post(MIDDLEWARE_ROUND_END_URL, json=data, timeout=1.5)
                    print("[SYNC] Round end notification sent to middleware")
                except Exception as error:
                    print(f"[WARN] Failed to notify middleware: {error}")

            round_data = {
                "round_number": ref.current_match, # Use current_match instead of current_round for clarity if needed
                "winner_team": winner_team,
                "winner_points": winner_points,
                "team1_points": ref.team1_points,
                "team2_points": ref.team2_points,
                "game_ended": ref.rounds_played >= MAX_RODADAS,
                "reason": "renuncia" if not round_ok else "score",
            }
            threading.Thread(target=_notify_round_end, args=(round_data,), daemon=True).start()

    _push_state(game_id)

    res = ref.state()
    res.update({
        "success": True,
        "message": "Card queued",
        "who_played": str(who_played),
        "next_player": str(ref.current_player),
        "queue_size": len(ref.card_queue),
    })
    return res


def correct_last_card(card: CardDTO):
    game_id = _normalize_game_id(card.game_id)
    ref = _get_ref(game_id)

    if not ref.card_queue and game_id in PRE_ROUND_SESSIONS:
        print(f"[DEBUG] Restoring state from pre-round backup for {game_id}")
        ref = copy.deepcopy(PRE_ROUND_SESSIONS[game_id])
        GAME_SESSIONS[game_id] = ref

    if not ref.card_queue and ref.trump_set and ref.rounds_played == 0:
        print(f"[DEBUG] Correcting trump card to: {card.rank} {card.suit}")
        card_id = _card_to_id(card)
        if card_id is None:
            return {"success": False, "message": "Invalid trump card"}

        old_trump_name = CardMapper.get_card(ref.trump) if ref.trump else "Unknown"

        if not ref.replace_trump(card_id):
            return {"success": False, "message": "Failed to replace trump"}

        # Sync CV for the old trump card
        try:
            old_rank = old_trump_name[:-1]
            old_suit = old_trump_name[-1]
            requests.post(
                CV_UNDO_URL,
                json={
                    "game_id": game_id,
                    "rank": old_rank,
                    "suit": old_suit,
                },
                timeout=1
            )
        except Exception:
            pass

        _push_state(game_id)
        res = ref.state()
        res.update({
            "success": True,
            "message": "Trump corrected",
            "who_played": str(ref.dealer),
        })
        return res

    if not ref.card_queue:
        return {"success": False, "message": "No pending card to correct"}

    print(f"[DEBUG] Correcting last card to: {card.rank} {card.suit}")
    card_id = _card_to_id(card)
    if card_id is None:
        return {"success": False, "message": "Invalid card"}

    if not ref.replace_last_card(card_id):
        return {"success": False, "message": "No pending card to correct"}

    print(f"[DEBUG] Card corrected. Queue size: {len(ref.card_queue)}")
    
    # Identify who played the corrected card for UI mapping
    # Avoid 'or' bug with player 0 (Este)
    base_idx = ref.trick_starter if ref.trick_starter is not None else ref.current_player
    p_idx = (base_idx + len(ref.card_queue) - 1) % 4
    
    # If the correction fills the trick (4th card), trigger trick resolution
    if len(ref.card_queue) >= 4:
        print("[DEBUG] Enough cards after correction, playing round...")
        # Note: PRE_ROUND_SESSIONS is already set if we restored from it, 
        # or we set it now if this is the first time the trick fills.
        if game_id not in PRE_ROUND_SESSIONS:
            PRE_ROUND_SESSIONS[game_id] = copy.deepcopy(ref)

        round_ok = ref.play_round()
        
        round_ended = False
        winner_team = None
        winner_points = 0

        if not round_ok:
            round_ended = True
            if ref.team1_victories > ref.team2_victories:
                winner_team = 1
                winner_points = ref.team1_victories
            else:
                winner_team = 2
                winner_points = ref.team2_victories
        elif ref.rounds_played >= MAX_RODADAS:
            round_ended = True
            ref.get_game_winner()
            if ref.team1_points > ref.team2_points:
                winner_team = 1
                winner_points = ref.team1_points
            else:
                winner_team = 2
                winner_points = ref.team2_points

        if round_ended:
            def _notify_round_end(data: dict):
                try:
                    requests.post(MIDDLEWARE_ROUND_END_URL, json=data, timeout=1.5)
                except Exception:
                    pass

            round_data = {
                "round_number": ref.current_match,
                "winner_team": winner_team,
                "winner_points": winner_points,
                "team1_points": ref.team1_points,
                "team2_points": ref.team2_points,
                "game_ended": ref.rounds_played >= MAX_RODADAS,
                "reason": "renuncia" if not round_ok else "score",
            }
            threading.Thread(target=_notify_round_end, args=(round_data,), daemon=True).start()

    _push_state(game_id)

    res = ref.state()
    res.update({
        "success": True,
        "message": "Card corrected",
        "who_played": str(p_idx),
        "queue_size": len(ref.card_queue),
    })
    return res


def undo_last_play(game_id: Optional[str] = None):
    normalized_game_id = _normalize_game_id(game_id)
    history = REF_HISTORY.get(normalized_game_id, [])
    if not history:
        return {"success": False, "message": "No play to undo"}

    old_ref, card_snapshot = history.pop()
    GAME_SESSIONS[normalized_game_id] = old_ref
    PRE_ROUND_SESSIONS.pop(normalized_game_id, None)

    try:
        if card_snapshot.get("rank") and card_snapshot.get("suit"):
            requests.post(
                CV_UNDO_URL,
                json={
                    "game_id": normalized_game_id,
                    "rank": card_snapshot.get("rank"),
                    "suit": card_snapshot.get("suit"),
                },
                timeout=1.0,
            )
            print(
                f"[UNDO] Notified CV service to undo card: "
                f"{card_snapshot.get('rank')} of {card_snapshot.get('suit')}"
            )
    except Exception as error:
        print(f"[WARN] Failed to notify CV service: {error}")

    _push_state(normalized_game_id)
    return {
        "success": True,
        "message": f"Undid play of {card_snapshot.get('rank')} of {card_snapshot.get('suit')}",
        "undone_player": str(old_ref.current_player),
        "game_state": old_ref.state(),
    }