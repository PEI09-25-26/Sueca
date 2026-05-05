"""
RandomAgent moved out of virtual_engine to agents service.
"""
from apps.virtual_engine.clients.client import GameClient
from apps.virtual_engine.game_state_tracker import GameStateTracker
from apps.virtual_engine.card_mapper import CardMapper
from .decision_maker import DecisionMaker
import random
import time


class RandomAgent(GameClient):
    def __init__(self, agent_name="RandomAI", game_id=None, position=None):
        super().__init__()
        self.agent_name = agent_name
        self.state_tracker = GameStateTracker()
        self.decision_maker = DecisionMaker(self.state_tracker)
        self.auto_play = True
        self.think_time = 1.0
        self.player_id = None
        self.game_id = game_id
        self.position = position
        self._last_phase = None
        self._last_finished_match = None

    def run(self):
        success, message, player_id = self.join_game(self.agent_name, self.game_id, self.position)
        if success:
            self.player_id = player_id
        if not success:
            print(f"[ERROR] Failed to join game: {message}")
            return

        self.player_name = self.agent_name
        print(f"RandomAgent joined as {self.player_name}\n")

        while True:
            state = self.get_status()
            if state is None:
                time.sleep(1)
                continue

            phase = state.get("phase")
            if self._last_phase == "finished" and phase in {"deck_cutting", "trump_selection", "playing"}:
                self.state_tracker.reset()

            self.state_tracker.update_from_state(state, self.player_name)
            hand = self.get_hand()
            self.state_tracker.update_my_hand(hand)

            if phase == "deck_cutting":
                self._handle_deck_cutting(state)
            elif phase == "trump_selection":
                self._handle_trump_selection(state)
            elif phase == "playing":
                self._handle_playing_turn(state)
            elif phase == "finished":
                match_number = state.get("current_match_number") or state.get("matches_played")
                if self._last_finished_match != match_number:
                    team1 = state.get("team_scores", {}).get("team1", 0)
                    team2 = state.get("team_scores", {}).get("team2", 0)
                    print(f"Game finished! Team 1: {team1} | Team 2: {team2}")
                    self._last_finished_match = match_number

            self._last_phase = phase
            time.sleep(random.uniform(0.5, 1.0))

    def _handle_deck_cutting(self, state):
        if state.get("north_player_id") != self.player_id and state.get("north_player") != self.player_name:
            return

        cut = self.decision_maker.choose_deck_cut()
        success, msg = self.cut_deck(cut)
        if success:
            print(f"Agent cutting deck at {cut}")
        else:
            print(f"[ERROR] Cutting deck failed: {msg}")

    def _handle_trump_selection(self, state):
        if state.get("west_player_id") != self.player_id and state.get("west_player") != self.player_name:
            return

        choice = self.decision_maker.choose_trump_selection()
        success, msg = self.select_trump(choice)
        if success:
            print(f"Agent selecting {choice} card for trump")
        else:
            print(f"[ERROR] Selecting trump failed: {msg}")

    def _handle_playing_turn(self, state):
        current_player_name = state.get("current_player_name") or state.get("current_player")
        if (
            state.get("current_player_id") != self.player_id
            and current_player_name != self.player_name
        ) or not self.state_tracker.my_hand:
            return

        time.sleep(self.think_time)

        card = self.decision_maker.choose_card(self.state_tracker.my_hand)
        if card is None:
            return

        card_str = str(card)
        success, msg = self.play_card(card_str)
        if success:
            card_display = CardMapper.get_card(card)
            print(f"Agent played: {card_display}")
        else:
            print(f"[ERROR] Playing card failed: {msg}")
