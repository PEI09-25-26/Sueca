from apps.virtual_engine.clients.client import GameClient
from apps.virtual_engine.game_state_tracker import GameStateTracker
from apps.virtual_engine.card_mapper import CardMapper
from .decision_maker import DecisionMaker
import time


class WeakAgent(GameClient):
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
        self._last_phase = None

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

            phase = state.get("phase")
            if phase == "playing":
                time.sleep(self.think_time)
                card = self.decision_maker.choose_card(self.state_tracker.my_hand)
                if card is None:
                    continue
                success, msg = self.play_card(str(card))
                if success:
                    print(f"Agent played: {CardMapper.get_card(card)}")
                else:
                    print(f"[ERROR] Playing card failed: {msg}")
