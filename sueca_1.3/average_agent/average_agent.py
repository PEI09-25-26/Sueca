"""AverageAgent - AI agent that plays Sueca using simple heuristics."""

from client import GameClient
from game_state_tracker import GameStateTracker
from card_mapper import CardMapper
from .decision_maker import DecisionMaker
from card_analyzer import CardAnalyzer
import os
import random
import time


class AverageAgent(GameClient):
    """
    AI agent that automatically plays Sueca.
    Inherits from GameClient to get server communication methods.
    """
    
    def __init__(self, agent_name="AverageAI", game_id=None, position=None):
        super().__init__()
        self.agent_name = agent_name
        self.state_tracker = GameStateTracker()
        self.decision_maker = DecisionMaker(self.state_tracker)
        self.auto_play = True
        self.think_time = float(os.getenv("SUECA_BOT_THINK_TIME", "0.0"))
        self.loop_sleep_min = float(os.getenv("SUECA_BOT_LOOP_SLEEP_MIN", "0.05"))
        self.loop_sleep_max = float(os.getenv("SUECA_BOT_LOOP_SLEEP_MAX", "0.10"))
        self.error_sleep = float(os.getenv("SUECA_BOT_ERROR_SLEEP", "0.1"))
        self.player_id = None
        self.game_id = game_id
        self.position = position
        self._last_phase = None
        self._last_match_number = None
        self._finished_announced_key = None

    def _maybe_handle_match_transition(self, state):
        current_phase = state.get("phase")
        current_match_number = state.get("current_match_number")
        current_round = state.get("current_round", 1)

        new_match_by_number = (
            current_match_number is not None
            and self._last_match_number is not None
            and current_match_number != self._last_match_number
        )
        new_match_after_finished = (
            self._last_phase == "finished"
            and current_phase in ("deck_cutting", "trump_selection", "playing")
            and current_round == 1
        )

        if new_match_by_number or new_match_after_finished:
            self.state_tracker.reset()
            self._finished_announced_key = None
            print("New match detected. Resetting AverageAgent tracker.")

        if current_match_number is not None:
            self._last_match_number = current_match_number
        self._last_phase = current_phase

    @staticmethod
    def _finished_key(state):
        return (state.get("current_match_number"), state.get("matches_played"))
    
    def run(self):
        """
        Main agent loop - overrides GameClient.run()
        This is the main entry point when you start the agent.
        """
        # Join the game
        self.player_name = self.agent_name
        success, message, player_id = self.join_game(self.player_name, self.game_id, self.position)
        if success:
            self.player_id = player_id
        if not success:
            print(f"[ERROR] Failed to join game: {message}")
            return
        
        print(f"AverageAgent joined as {self.player_name}\n")
        
        while True:
            try:
                state = self.get_status()
                if state is None:
                    time.sleep(self.error_sleep)
                    continue

                self._maybe_handle_match_transition(state)

                # Update state tracker
                self.state_tracker.update_from_state(state, self.player_name)

                # Fetch hand only when it can affect a move to avoid flooding the server.
                if state.get("phase") == "playing":
                    current_player_name = state.get("current_player_name") or state.get("current_player")
                    is_my_turn = (
                        state.get("current_player_id") == self.player_id
                        or current_player_name == self.player_name
                    )
                    if is_my_turn:
                        hand = self.get_hand()
                        self.state_tracker.update_my_hand(hand)

                # Handle deck cutting
                if state["phase"] == "deck_cutting":
                    self._handle_deck_cutting(state)

                # Handle trump selection
                elif state["phase"] == "trump_selection":
                    self._handle_trump_selection(state)

                # Handle playing turn
                elif state["phase"] == "playing":
                    self._handle_playing_turn(state)

                # Game finished
                elif state["phase"] == "finished":
                    finished_key = self._finished_key(state)
                    if self._finished_announced_key != finished_key:
                        team1 = state.get("team_scores", {}).get("team1", 0)
                        team2 = state.get("team_scores", {}).get("team2", 0)
                        print(f"Game finished! Team 1: {team1} | Team 2: {team2}")
                        self._finished_announced_key = finished_key
            except Exception as error:
                print(f"[ERROR] AverageAgent loop error: {error}")
                time.sleep(self.error_sleep)

            time.sleep(random.uniform(self.loop_sleep_min, self.loop_sleep_max))
    
    def _handle_deck_cutting(self, state):
        """
        Handle if we're NORTH and need to cut the deck.
        """
        if state.get("north_player") != self.player_name:
            return
        
        cut = self.decision_maker.choose_deck_cut()
        success, msg = self.cut_deck(cut)
        if success:
            print(f"Agent cutting deck at {cut}")
        else:
            print(f"[ERROR] Cutting deck failed: {msg}")
    
    def _handle_trump_selection(self, state):
        """
        Handle if we're WEST and need to choose trump.
        """
        if state.get("west_player") != self.player_name:
            return
        
        choice = self.decision_maker.choose_trump_selection()
        success, msg = self.select_trump(choice)
        if success:
            print(f"Agent selecting {choice} card for trump")
        else:
            print(f"[ERROR] Selecting trump failed: {msg}")
        
    
    def _handle_playing_turn(self, state):
        """
        Handle if it's our turn to play a card.
        """
        if state.get("current_player") != self.player_name or not self.state_tracker.my_hand:
            return
        
        time.sleep(self.think_time)

        hand_before = list(self.state_tracker.my_hand)  # ✅ snapshot

        legal_moves = CardAnalyzer.get_legal_plays(
            hand_before,
            self.state_tracker.lead_suit
        )
        
        card = self.decision_maker.choose_card(self.state_tracker.my_hand)
        if card is None:
            return
        
        print(f"[DEBUG] {self.player_name} logging action, game_id={self.game_id}")
        self.log_action({
            "round_number": self.state_tracker.current_round,
            "player": self.player_name,
            "position": self.position,
            "hand_before": hand_before,
            "legal_moves": legal_moves,
            "chosen_card": card,
            "cards_in_trick": list(self.state_tracker.current_trick),
            "position_in_trick": len(self.state_tracker.current_trick),
            "lead_suit": self.state_tracker.lead_suit,
            "trump": self.state_tracker.trump_suit,
        })

        card_str = str(card)
        success, msg = self.play_card(card_str)
        if success:
            card_display = CardMapper.get_card(card)
            print(f"Agent played: {card_display}")
        else:
            print(f"[ERROR] Playing card failed: {msg}")


# Backward-compatible alias for older imports.
AverageClient = AverageAgent