"""WeakAgent - AI agent that plays Sueca using simple heuristics."""

import random
import time

from ...card_mapper import CardMapper
from ...clients.client import GameClient
from ...game_state_tracker import GameStateTracker
from .decision_maker import DecisionMaker


class WeakAgent(GameClient):
    """Heuristic weak bot adapted for Sueca 1.4 API signatures."""

    def __init__(self, agent_name="WeakAI", game_id=None, position=None):
        super().__init__()
        self.agent_name = agent_name
        self.state_tracker = GameStateTracker()
        self.decision_maker = DecisionMaker(self.state_tracker)
        self.auto_play = True
        self.think_time = 1.0
        self.player_id = None
        self.game_id = game_id
        self.position = position

    def run(self):
        success, message, player_id = self.join_game(self.agent_name, self.game_id, self.position)
        if not success:
            print(f"[ERROR] Failed to join game: {message}")
            return

        self.player_name = self.agent_name
        self.player_id = player_id
        print(f"WeakAgent joined as {self.player_name}\n")

        while True:
            state = self.get_status()
            if state is None:
                time.sleep(1)
                continue

            self.state_tracker.update_from_state(state, self.player_name)
            hand = self.get_hand()
            self.state_tracker.update_my_hand(hand)

            if state["phase"] == "deck_cutting":
                self._handle_deck_cutting(state)
            elif state["phase"] == "trump_selection":
                self._handle_trump_selection(state)
            elif state["phase"] == "playing":
                self._handle_playing_turn(state)
            elif state["phase"] == "finished":
                team1 = state.get("team_scores", {}).get("team1", 0)
                team2 = state.get("team_scores", {}).get("team2", 0)
                print(f"Game finished! Team 1: {team1} | Team 2: {team2}")
                break

            time.sleep(random.uniform(0.5, 1.0))

    def _handle_deck_cutting(self, state):
        if state.get("north_player") != self.player_name:
            return

        cut = self.decision_maker.choose_deck_cut()
        success, message = self.cut_deck(cut)
        if success:
            print(f"Agent cutting deck at {cut}")
        else:
            print(f"[ERROR] Cutting deck failed: {message}")

    def _handle_trump_selection(self, state):
        if state.get("west_player") != self.player_name:
            return

        choice = self.decision_maker.choose_trump_selection()
        success, message = self.select_trump(choice)
        if success:
            print(f"Agent selecting {choice} card for trump")
        else:
            print(f"[ERROR] Selecting trump failed: {message}")

    def _handle_playing_turn(self, state):
        if state.get("current_player") != self.player_name or not self.state_tracker.my_hand:
            return

        time.sleep(self.think_time)

        card = self.decision_maker.choose_card(self.state_tracker.my_hand)
        if card is None:
            return

        success, message = self.play_card(str(card))
        if success:
            print(f"Agent played: {CardMapper.get_card(card)}")
        else:
            print(f"[ERROR] Playing card failed: {message}")
