from apps.virtual_engine.card_analyzer import CardAnalyzer


class DecisionMaker:
    def __init__(self, state_tracker):
        self.state = state_tracker

    def choose_card(self, hand):
        legal = CardAnalyzer.get_legal_plays(hand, self.state.lead_suit)
        if not legal:
            return None
        # choose lowest-value card
        return CardAnalyzer.get_lowest_card(legal)
