from apps.virtual_engine.card_analyzer import CardAnalyzer
from apps.virtual_engine.card_mapper import CardMapper


class DecisionMaker:
    def __init__(self, state_tracker):
        self.state = state_tracker

    def choose_card(self, hand):
        legal = CardAnalyzer.get_legal_plays(hand, self.state.lead_suit)
        if not legal:
            return None
        # random choice among legal plays
        import random

        return random.choice(legal)

    def choose_trump_selection(self):
        import random

        return random.choice(["top", "bottom"])

    def choose_deck_cut(self):
        import random

        return random.randint(1, 40)
