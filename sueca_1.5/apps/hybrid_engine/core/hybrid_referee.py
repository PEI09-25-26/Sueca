from typing import Dict, List, Tuple
from apps.hybrid_engine.card_mapper import CardMapper
import copy

class HybridReferee:
    """Tracks suit availability for hybrid players to detect renúncias (revokes)."""
    
    def __init__(self):
        # game_id -> {player_id: [has_clubs, has_diamonds, has_hearts, has_spades]}
        self.suit_tracking: Dict[str, Dict[str, List[bool]]] = {}
        # game_id -> list of tracking snapshots for undo
        self.history: Dict[str, List[Dict[str, List[bool]]]] = {}

    def _ensure_game(self, game_id: str):
        if game_id not in self.suit_tracking:
            self.suit_tracking[game_id] = {}
        if game_id not in self.history:
            self.history[game_id] = []

    def _ensure_player(self, game_id: str, player_id: str):
        self._ensure_game(game_id)
        if player_id not in self.suit_tracking[game_id]:
            self.suit_tracking[game_id][player_id] = [True, True, True, True]

    def reset_game(self, game_id: str):
        if game_id in self.suit_tracking:
            del self.suit_tracking[game_id]
        if game_id in self.history:
            del self.history[game_id]

    def check_play(
        self, game_id: str, player_id: str, card_id: int, round_suit: str
    ) -> Tuple[bool, str]:
        """Returns (is_renuncia, reason). Analyzes without modifying state."""
        self._ensure_player(game_id, player_id)

        card_suit = CardMapper.get_card_suit(card_id)
        card_suit_index = CardMapper.SUITS.index(card_suit)

        # Known void in the suit being played (includes opening lead of a new trick).
        if not self.suit_tracking[game_id][player_id][card_suit_index]:
            return True, "Falta de assistência. Jogou naipe de que não tinha cartas."

        return False, ""

    def record_play(self, game_id: str, player_id: str, card_id: int, round_suit: str):
        """Saves current state to history and updates tracking for the new play."""
        self._ensure_player(game_id, player_id)
        
        # Save snapshot
        self.history[game_id].append(copy.deepcopy(self.suit_tracking[game_id]))

        if not round_suit:
            return # First play, doesn't reveal voids

        card_suit = CardMapper.get_card_suit(card_id)
        # If they didn't follow suit, they are void in the round suit
        if card_suit != round_suit:
            round_suit_index = CardMapper.SUITS.index(round_suit)
            self.suit_tracking[game_id][player_id][round_suit_index] = False

    def undo_play(self, game_id: str):
        """Restores the tracking state to before the last play."""
        if game_id in self.history and self.history[game_id]:
            self.suit_tracking[game_id] = self.history[game_id].pop()
