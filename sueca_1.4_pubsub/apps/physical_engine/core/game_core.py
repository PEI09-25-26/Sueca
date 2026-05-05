from typing import Optional
import requests
from pydantic import BaseModel
import threading
import time

from ..card_mapper import CardMapper
from ..referee import Referee

ref = Referee()
state_sync_lock = threading.Lock()

MIDDLEWARE_URL = "http://localhost:8000/game/state"
MIDDLEWARE_ROUND_END_URL = "http://localhost:8000/game/round_end"

# Game constants
MAX_ROUNDS = 4
MAX_RODADAS = 10
current_round = 1
current_hand = ref.current_player - 1


class CardDTO(BaseModel):
	rank: str
	suit: str
	confidence: Optional[float] = None


def get_state_data():
	return ref.state()


def _send_state_to_middleware():
	with state_sync_lock:
		time.sleep(0.05)
		try:
			requests.post(MIDDLEWARE_URL, json=ref.state(), timeout=1.0)
			print("[SYNC] State pushed to middleware")
		except requests.exceptions.RequestException as error:
			print(f"[WARN] State sync failed: {error}")


def _push_state():
	threading.Thread(target=_send_state_to_middleware, daemon=True).start()


def reset_game_state():
	global ref, current_round
	ref = Referee()
	current_round = 1
	return {"success": True, "message": "Game reset"}


def start_new_round():
	global ref, current_round
	team1_vict = ref.team1_victories
	team2_vict = ref.team2_victories
	ref = Referee()
	ref.team1_victories = team1_vict
	ref.team2_victories = team2_vict
	current_round += 1
	return {
		"success": True,
		"message": f"Nova ronda {current_round} iniciada",
		"round": current_round,
	}


def process_card(card: CardDTO):
	global current_hand
	if len(ref.card_queue) == 0:
		current_hand = ref.current_player - 1

	print(f"[DEBUG] Received card: {card.rank} {card.suit}")
	try:
		rank_index = CardMapper.RANKS.index(card.rank)
		suit_index = CardMapper.SUITS.index(card.suit)
		card_id = suit_index * CardMapper.SUITSIZE + rank_index
	except ValueError:
		print("[DEBUG] Invalid card!")
		return {"success": False, "message": "Invalid card"}

	ref.inject_card(card_id)
	print(f"[DEBUG] Card injected. Queue size: {len(ref.card_queue)}")

	if not ref.trump_set:
		print("[DEBUG] Setting trump...")
		ref.set_trump()
		print(f"[DEBUG] Trump now: {CardMapper.get_card(ref.trump)} (suit: {ref.trump_suit})")
		_push_state()
		current_hand -= 1
		return {
			"success": True,
			"message": "Trump card set",
		}

	current_hand += 1

	if len(ref.card_queue) >= 4:
		print("[DEBUG] Enough cards for a round, playing round...")
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
			if ref.team1_points > ref.team2_points:
				winner_team = 1
				winner_points = ref.team1_points
			else:
				winner_team = 2
				winner_points = ref.team2_points
			print(f"[RONDA] Acabou apos 10 rodadas! Equipa {winner_team} ganhou com {winner_points} pontos")

		if round_ended:
			try:
				round_data = {
					"round_number": current_round,
					"winner_team": winner_team,
					"winner_points": winner_points,
					"team1_points": ref.team1_points,
					"team2_points": ref.team2_points,
					"game_ended": current_round >= MAX_ROUNDS,
				}
				requests.post(MIDDLEWARE_ROUND_END_URL, json=round_data, timeout=1)
				print("[SYNC] Round end notification sent to middleware")
			except Exception as error:
				print(f"[WARN] Failed to notify middleware: {error}")

		_push_state()

	return {
		"success": True,
		"message": "Card queued",
		"current_player": current_hand % 4,
		"queue_size": len(ref.card_queue),
	}
