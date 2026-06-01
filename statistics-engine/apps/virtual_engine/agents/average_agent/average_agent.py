"""AverageAgent - AI agent that plays Sueca using simple heuristics."""

import os
import random
import time

from ...card_mapper import CardMapper
from ...clients.client import GameClient
from ...game_state_tracker import GameStateTracker
from .decision_maker import DecisionMaker


def _env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return float(default)


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {'1', 'true', 'yes', 'on'}


class AverageAgent(GameClient):
    """Heuristic average bot"""

    def __init__(self, agent_name="AverageAI", game_id=None, position=None):
        super().__init__()
        self.agent_name = agent_name
        self.state_tracker = GameStateTracker()
        self.decision_maker = DecisionMaker(self.state_tracker)
        self.auto_play = True
        self.think_time = max(0.0, _env_float("SUECA_BOT_THINK_TIME", 0.0))
        self.loop_sleep_min = max(0.0, _env_float("SUECA_BOT_LOOP_SLEEP_MIN", 0.0))
        self.loop_sleep_max = max(self.loop_sleep_min, _env_float("SUECA_BOT_LOOP_SLEEP_MAX", 0.0))
        self.error_sleep = max(0.0, _env_float("SUECA_BOT_ERROR_SLEEP", 0.0))
        self.verbose = _env_bool("SUECA_BOT_VERBOSE", False)
        self.min_loop_sleep = max(0.001, self.loop_sleep_min)
        self.player_id = None
        self.game_id = game_id
        self.position = position
        self._last_phase = None
        self._last_finished_match = None
        

    def run(self):
        success, message, player_id = self.join_game(self.agent_name, self.game_id, self.position)
        if not success:
            if self.verbose:
                print(f"[ERROR] Failed to join game: {message}")
            return

        self.player_name = self.agent_name
        self.player_id = player_id
        if self.verbose:
            print(f"AverageAgent joined as {self.player_name}\n")

        while True:
            state = self.get_status()
            if state is None:
                continue

            phase = state.get("phase")
            if self._last_phase == "finished" and phase in {"deck_cutting", "trump_selection", "playing"}:
                self.state_tracker.reset()

            self.state_tracker.update_from_state(state, self.player_name)

            current_player_name = state.get("current_player_name") or state.get("current_player")
            is_my_turn = state.get("current_player_id") == self.player_id or current_player_name == self.player_name
            if phase == "playing" and is_my_turn and not self.state_tracker.my_hand:
                self.state_tracker.update_my_hand(self.get_hand())

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
                    if self.verbose:
                        print(f"Game finished! Team 1: {team1} | Team 2: {team2}")
                    self._last_finished_match = match_number
                    break

            self._last_phase = phase
            time.sleep(self.min_loop_sleep)


    def _handle_deck_cutting(self, state):
        if state.get("north_player_id") != self.player_id and state.get("north_player") != self.player_name:
            return

        cut = self.decision_maker.choose_deck_cut()
        success, message = self.cut_deck(cut)
        if success:
            if self.verbose:
                print(f"Agent cutting deck at {cut}")
        else:
            if self.verbose:
                print(f"[ERROR] Cutting deck failed: {message}")

    def _handle_trump_selection(self, state):
        if state.get("west_player_id") != self.player_id and state.get("west_player") != self.player_name:
            return

        choice = self.decision_maker.choose_trump_selection()
        success, message = self.select_trump(choice)
        if success:
            if self.verbose:
                print(f"Agent selecting {choice} card for trump")
        else:
            if self.verbose:
                print(f"[ERROR] Selecting trump failed: {message}")

    def _handle_playing_turn(self, state):
        current_player_name = state.get("current_player_name") or state.get("current_player")
        if (
            state.get("current_player_id") != self.player_id
            and current_player_name != self.player_name
        ) or not self.state_tracker.my_hand:
            return

    
        card = self.decision_maker.choose_card(self.state_tracker.my_hand)
        if card is None:
            return

        success, message = self.play_card(str(card))
        if success:
            played_card = int(card)
            if played_card in self.state_tracker.my_hand:
                self.state_tracker.my_hand.remove(played_card)
            if self.verbose:
                print(f"Agent played: {CardMapper.get_card(card)}")
        else:
            if self.verbose:
                print(f"[ERROR] Playing card failed: {message}")
