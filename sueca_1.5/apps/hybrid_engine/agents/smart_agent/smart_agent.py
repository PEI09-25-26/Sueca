"""SmartAgent - hybrid-mode heuristic bot."""

from ..hybrid_bot_base import HybridBotAgent
from .decision_maker import DecisionMaker


class SmartAgent(HybridBotAgent):
    def __init__(self, agent_name="SmartAI", game_id=None, position=None):
        super().__init__(agent_name=agent_name, game_id=game_id, position=position)

    def _build_decision_maker(self):
        return DecisionMaker(self.state_tracker)
