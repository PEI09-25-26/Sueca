"""Shared runtime loop for hybrid-mode AI bots."""

from __future__ import annotations

import random
import time
from typing import Optional

from ..card_mapper import CardMapper
from ..clients.client import GameClient
from ..game_state_tracker import GameStateTracker


class HybridBotAgent(GameClient):
    """Bot that plays through hybrid APIs as a virtual player (no camera)."""

    decision_maker = None  # set by subclasses

    def __init__(self, agent_name="HybridBot", game_id=None, position=None):
        super().__init__()
        self.agent_name = agent_name
        self.state_tracker = GameStateTracker()
        self.auto_play = True
        self.think_time = 1.0
        self.player_id = None
        self.game_id = game_id
        self.position = position
        self._last_phase = None
        self._last_finished_match = None
        self._registered_hybrid = False

    def _build_decision_maker(self):
        raise NotImplementedError

    def run(self):
        self.decision_maker = self._build_decision_maker()

        success, message, player_id = self.join_game(self.agent_name, self.game_id, self.position)
        if not success:
            print(f"[ERROR] Failed to join game: {message}")
            return

        self.player_name = self.agent_name
        self.player_id = player_id
        print(f"{self.agent_name} joined hybrid game as {self.player_name}\n")

        if not self._register_as_hybrid_bot():
            print(f"[ERROR] Failed to register hybrid bot role: {self.agent_name}")
            return

        while self.auto_play:
            state = self.get_status()
            if state is None:
                time.sleep(1)
                continue

            phase = state.get("phase")
            if self._last_phase == "finished" and phase in {"deck_cutting", "trump_selection", "playing"}:
                self.state_tracker.reset()

            self.state_tracker.update_from_state(state, self.player_name)
            hand = self._resolve_hand()
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

    def _register_as_hybrid_bot(self) -> bool:
        data = self._post(
            "/api/hybrid/bot/register",
            {
                "game_id": self.game_id,
                "player_id": self.player_id,
            },
        )
        if data.get("success"):
            self._registered_hybrid = True
        return bool(data.get("success"))

    def _resolve_hand(self) -> list:
        hybrid = self._get_hybrid_state()
        if hybrid:
            for entry in hybrid.get("virtual_players", []):
                if entry.get("player_id") == self.player_id:
                    cards = entry.get("cards") or []
                    return [int(c) for c in cards]
        return self.get_hand()

    def _get_hybrid_state(self) -> Optional[dict]:
        data = self._get("/api/hybrid/state", params={"game_id": self.game_id})
        if data.get("success"):
            return data.get("state")
        return None

    def _is_deal_ready(self) -> bool:
        hybrid = self._get_hybrid_state()
        if not hybrid:
            return False
        return bool(hybrid.get("deal_done"))

    def _handle_deck_cutting(self, state):
        # Hybrid: the host cuts the physical deck with the camera; bots do not cut server-side.
        return

    def _handle_trump_selection(self, state):
        if state.get("west_player_id") != self.player_id and state.get("west_player") != self.player_name:
            return

        hybrid = self._get_hybrid_state() or {}
        if hybrid.get("pending_trump_side"):
            return

        choice = self.decision_maker.choose_trump_selection()
        data = self._post(
            "/api/hybrid/trump/select_side",
            {
                "game_id": self.game_id,
                "player_id": self.player_id,
                "choice": choice,
            },
        )
        if data.get("success"):
            print(f"{self.agent_name} chose trump side: {choice} (waiting for host capture)")
        else:
            print(f"[ERROR] Trump side selection failed: {data.get('message')}")

    def _handle_playing_turn(self, state):
        if not self._is_deal_ready():
            return

        current_player_name = state.get("current_player_name") or state.get("current_player")
        if (
            state.get("current_player_id") != self.player_id
            and current_player_name != self.player_name
        ):
            return

        hand = self._resolve_hand()
        if not hand:
            return

        self.state_tracker.update_my_hand(hand)
        time.sleep(self.think_time)

        card = self.decision_maker.choose_card(hand)
        if card is None:
            return

        success, message = self.bot_play_card(int(card))
        if success:
            print(f"{self.agent_name} played: {CardMapper.get_card(card)}")
        else:
            print(f"[ERROR] Playing card failed: {message}")

    def bot_play_card(self, card_id: int):
        """Select card like a virtual player; host confirms physically via camera."""
        data = self._post(
            "/api/hybrid/virtual/select_card",
            {
                "game_id": self.game_id,
                "player_id": self.player_id,
                "card": int(card_id),
            },
            timeout=5,
        )
        if not data.get("success"):
            return False, data.get("message", "Unknown error")
        return self._wait_for_host_confirmation(int(card_id))

    def _wait_for_host_confirmation(self, card_id: int, timeout: float = 120.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            hybrid = self._get_hybrid_state() or {}
            pending = hybrid.get("pending_virtual_play")
            state = self.get_status() or {}

            if pending is None:
                for play in state.get("round_plays", []):
                    if play.get("player_id") == self.player_id and int(play.get("card", -1)) == int(card_id):
                        return True, "Play confirmed by host"
                if state.get("current_player_id") != self.player_id:
                    return True, "Turn advanced"

            time.sleep(0.35)

        return False, "Timed out waiting for host to confirm bot card on table"
